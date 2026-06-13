# -*- coding: utf-8 -*-
"""
Esegue l'INTERA pipeline su un argomento d'esempio e salva i risultati in backend/out/:
  - graph.json        : nodi + archi pesati + vettore profilo (dati grezzi del backend)
  - nexus_real.json    : stesso grafo nello schema del frontend (per caricarlo nel globo)

Uso:
    python export_demo.py "spiking neural networks" "optimization" "neuromorphic computing"

Cosi' dimostriamo la connessione: dati 100% reali da Semantic Scholar, ma "cotti" in un
file statico -> il globo resta veloce e offline-safe per il pitch.
"""
import os
import sys
import json

import config
import vectormath as vm
from query_builder import build_queries
from pipeline import get_seed_papers, build_graph_and_profile

# i 3 cluster del frontend (riuso le chiavi/colori gia' presenti nel globo)
FRONT_CLUSTERS = ["comp-neuro", "deep-learning", "neuroai-bridge"]


def kmeans(vectors, k=3, iters=12):
    """k-means minimale in puro Python. Ritorna l'etichetta cluster per ogni vettore."""
    pts = [(i, v) for i, v in enumerate(vectors) if v]
    if len(pts) < k:
        return [0] * len(vectors)
    centroids = [pts[i * len(pts) // k][1][:] for i in range(k)]
    labels = [0] * len(vectors)
    for _ in range(iters):
        # assegna
        for i, v in pts:
            best, bd = 0, -2
            for c in range(k):
                s = vm.cosine(v, centroids[c])
                if s > bd:
                    bd, best = s, c
            labels[i] = best
        # aggiorna i centroidi
        for c in range(k):
            members = [v for i, v in pts if labels[i] == c]
            if members:
                centroids[c] = vm.mean_vector(members)
    return labels


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "spiking neural networks"
    method = sys.argv[2] if len(sys.argv) > 2 else "optimization"
    field = sys.argv[3] if len(sys.argv) > 3 else "neuromorphic computing"

    print("Argomento: topic=%r metodo=%r campo=%r" % (topic, method, field))
    queries = build_queries(topic, method, field)
    print("Query:", queries)

    seeds = get_seed_papers(queries, sort_choice="citations", per_query=2)
    print("Paper seed trovati:", len(seeds))
    if not seeds:
        print("Nessun paper trovato — prova un argomento diverso.")
        return

    # simulazione scelta utente: i primi 3 seed = positivi, gli altri = negativi
    positive = [s["paperId"] for s in seeds[:3]]
    negative = [s["paperId"] for s in seeds[3:]]

    g = build_graph_and_profile(positive, negative, keep_vectors=True)
    print("Grafo:", json.dumps(g["stats"]))

    # clustering in 3 gruppi per dare un colore ai nodi nel globo
    nodes = g["nodes"]
    labels = kmeans([n.get("embedding") for n in nodes], k=3)

    # heuristica nodo-ponte: nodo i cui vicini coprono >= 2 cluster diversi
    neigh = {n["id"]: set() for n in nodes}
    label_by_id = {n["id"]: labels[i] for i, n in enumerate(nodes)}
    for e in g["edges"]:
        neigh[e["source"]].add(e["target"])
        neigh[e["target"]].add(e["source"])

    # nodo-ponte = pochi nodi con piu' vicini in cluster DIVERSI dal proprio.
    # Tengo solo i top ~6 (con almeno 2 collegamenti cross-cluster), altrimenti diventano tutti "ponte".
    bridge_score = {}
    for i, n in enumerate(nodes):
        nbrs = neigh.get(n["id"], set())
        bridge_score[n["id"]] = sum(1 for x in nbrs if label_by_id.get(x) != labels[i])
    bridge_ids = set()
    for n in sorted(nodes, key=lambda n: -bridge_score[n["id"]]):
        if bridge_score[n["id"]] >= 2 and len(bridge_ids) < 6:
            bridge_ids.add(n["id"])

    papers = []
    for i, n in enumerate(nodes):
        cl = labels[i]
        is_bridge = n["id"] in bridge_ids
        papers.append({
            "id": n["id"],
            "title": n["title"],
            "authors": n["authors"],
            "year": n["year"],
            "citationCount": n["citationCount"],
            "citationVelocity": n["citationVelocity"],
            "cluster": FRONT_CLUSTERS[cl % 3],
            "isBridge": bool(is_bridge),
            "summary": n["abstract"] or "",
        })

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out_dir, exist_ok=True)

    # rimuovo gli embedding dal grafo grezzo prima di salvarlo (file enorme altrimenti)
    for n in nodes:
        n.pop("embedding", None)
    with open(os.path.join(out_dir, "graph.json"), "w", encoding="utf-8") as f:
        json.dump(g, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out_dir, "nexus_real.json"), "w", encoding="utf-8") as f:
        json.dump({"papers": papers}, f, ensure_ascii=False, indent=2)

    # file JS che il globo carica direttamente (window.NEXUS_REAL), nella root del progetto
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    js_path = os.path.join(root_dir, "nexus_real.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("window.NEXUS_REAL = " + json.dumps({"papers": papers}, ensure_ascii=False) + ";\n")

    print("\nSalvati:")
    print("  backend/out/graph.json       (nodi+archi+vettore profilo)")
    print("  backend/out/nexus_real.json  (%d paper, schema frontend)" % len(papers))
    print("  nexus_real.js                (caricato dalla linguetta 'Reali' del globo)")
    print("  Nodi-ponte individuati:", sum(1 for p in papers if p["isBridge"]))


if __name__ == "__main__":
    main()
