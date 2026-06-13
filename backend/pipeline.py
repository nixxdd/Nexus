# -*- coding: utf-8 -*-
"""
Pipeline NEXUS — dal testo dell'onboarding fino al GRAFO + VETTORE PROFILO.

Fasi:
  1) build_queries()           -> 3 query (in query_builder.py)
  2) get_seed_papers()         -> 2 paper per query (card da mostrare all'utente)
  3) build_graph_and_profile() -> recommendations + embeddings + archi pesati + vettore profilo

L'agente RAG finale NON e' qui (resta lato interfaccia, come da specifica).
"""
import itertools

import config
import s2_client as s2
import vectormath as vm
from query_builder import build_queries, sort_param


# ----------------------------------------------------------------- helper

def _authors(paper):
    out = []
    for a in (paper.get("authors") or []):
        nm = a.get("name")
        if nm:
            out.append(nm)
    return out

def _refs_set(paper):
    s = set()
    for r in (paper.get("references") or []):
        pid = r.get("paperId") if isinstance(r, dict) else None
        if pid:
            s.add(pid)
    return s

def _embedding(paper):
    emb = paper.get("embedding")
    if emb and isinstance(emb, dict):
        return emb.get("vector")
    return None

def _velocity(citation_count, year):
    if not year:
        return float(citation_count or 0)
    age = max(1, config.CURRENT_YEAR - int(year) + 1)
    return round((citation_count or 0) / age, 1)

def _recency_weight(year):
    """Paper recenti pesano un po' di piu' nel vettore profilo (dal brief)."""
    if not year:
        return 1.0
    age = config.CURRENT_YEAR - int(year)
    return max(0.6, 1.2 - age * 0.03)


# ----------------------------------------------------- FASE 2: paper seed

def get_seed_papers(queries, sort_choice="citations", per_query=2):
    """Per ogni query prende 'per_query' paper. Ritorna le card per l'utente."""
    sort = sort_param(sort_choice)
    seeds = []
    seen = set()
    for qi, q in enumerate(queries):
        if sort == "MIXED":
            by_cit = s2.search_bulk(q, sort="citationCount:desc", limit=per_query)
            by_year = s2.search_bulk(q, sort="publicationDate:desc", limit=per_query)
            merged = list(itertools.chain.from_iterable(zip(by_cit, by_year)))
        else:
            merged = s2.search_bulk(q, sort=sort, limit=per_query + 2)
        taken = 0
        for p in merged:
            pid = p.get("paperId")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            seeds.append({
                "paperId": pid,
                "title": p.get("title"),
                "authors": _authors(p),
                "year": p.get("year"),
                "citationCount": p.get("citationCount") or 0,
                "abstract": (p.get("abstract") or "")[:400],
                "query": q,
                "queryIndex": qi,
            })
            taken += 1
            if taken >= per_query:
                break
    return seeds


# -------------------------------------- FASE 3: grafo + vettore profilo

def build_graph_and_profile(positive_ids, negative_ids=None, feedback=None,
                            rec_limit=40, edge_top_k=6, keep_vectors=False):
    """
    positive_ids : id dei paper scelti dall'utente (pollice su)
    negative_ids : id scartati / gia' nel grafo (diventano negativi per le recommendations)
    feedback     : dict opzionale {(idA,idB): valore in [-1,1]} per il termine di feedback
    Ritorna: {nodes, edges, profileVector, stats}
    """
    positive_ids = [p for p in (positive_ids or []) if p]
    negative_ids = [n for n in (negative_ids or []) if n]
    feedback = feedback or {}

    # 1) espansione semantica via Recommendations API
    recommended = s2.recommend(positive_ids, negative_ids, limit=rec_limit)
    rec_ids = [p.get("paperId") for p in recommended if p.get("paperId")]

    # 2) nodi = positivi + raccomandati (dedup, esclusi i negativi)
    neg_set = set(negative_ids)
    node_ids, seen = [], set()
    for pid in positive_ids + rec_ids:
        if pid and pid not in seen and pid not in neg_set:
            seen.add(pid)
            node_ids.append(pid)

    # 3) dettagli + embedding (un'unica chiamata batch)
    details = s2.get_papers_batch(node_ids)
    nodes = []
    by_id = {}
    for p in details:
        if not p:
            continue
        pid = p.get("paperId")
        node = {
            "id": pid,
            "title": p.get("title"),
            "authors": _authors(p),
            "year": p.get("year"),
            "citationCount": p.get("citationCount") or 0,
            "citationVelocity": _velocity(p.get("citationCount"), p.get("year")),
            "abstract": (p.get("abstract") or "")[:500],
            "isSeed": pid in set(positive_ids),
            "_emb": _embedding(p),
            "_refs": _refs_set(p),
        }
        nodes.append(node)
        by_id[pid] = node

    # 4) VETTORE PROFILO = media pesata (per recency) degli embedding dei paper scelti
    pos_vectors, pos_weights = [], []
    for pid in positive_ids:
        n = by_id.get(pid)
        if n and n["_emb"]:
            pos_vectors.append(n["_emb"])
            pos_weights.append(_recency_weight(n["year"]))
    profile_vector = vm.mean_vector(pos_vectors, pos_weights)

    # 5) rilevanza di ogni nodo rispetto al profilo (utile per ranking / colore)
    for n in nodes:
        n["profileSim"] = round(vm.cosine(profile_vector, n["_emb"]), 4) if (profile_vector and n["_emb"]) else 0.0

    # 6) archi pesati: peso = 0.5*coseno + 0.3*co-citazione + 0.15*citazione_diretta + 0.05*feedback
    edges = []
    for a, b in itertools.combinations(nodes, 2):
        sim = vm.cosine(a["_emb"], b["_emb"]) if (a["_emb"] and b["_emb"]) else 0.0
        cocite = vm.jaccard(a["_refs"], b["_refs"])          # riferimenti condivisi (bibliographic coupling)
        direct = 1.0 if (b["id"] in a["_refs"] or a["id"] in b["_refs"]) else 0.0
        fb = feedback.get((a["id"], b["id"]), feedback.get((b["id"], a["id"]), 0.0))
        weight = (config.W_COSINE * sim + config.W_COCITE * cocite +
                  config.W_DIRECT * direct + config.W_FEEDBACK * fb)
        if weight >= config.EDGE_THRESHOLD:
            edges.append({"source": a["id"], "target": b["id"],
                          "weight": round(weight, 4), "cosine": round(sim, 4)})

    # 6b) anti-"hairball": tieni al massimo i top-K archi per nodo
    if edge_top_k:
        keep = set()
        per = {}
        for e in sorted(edges, key=lambda e: -e["weight"]):
            for nid in (e["source"], e["target"]):
                per.setdefault(nid, 0)
            if per[e["source"]] < edge_top_k or per[e["target"]] < edge_top_k:
                keep.add(id(e))
                per[e["source"]] += 1
                per[e["target"]] += 1
        edges = [e for e in edges if id(e) in keep]

    # pulizia campi interni prima dell'output
    for n in nodes:
        if keep_vectors:
            n["embedding"] = n["_emb"]   # l'export lo usa per clusterizzare
        n.pop("_emb", None)
        n["_refs"] = len(n["_refs"])  # tengo solo il conteggio, non la lista

    stats = {
        "nPositive": len(positive_ids),
        "nNegative": len(negative_ids),
        "nRecommended": len(rec_ids),
        "nNodes": len(nodes),
        "nEdges": len(edges),
        "profileDim": len(profile_vector),
    }
    return {"nodes": nodes, "edges": edges, "profileVector": profile_vector, "stats": stats}


# ------------------------------------------------------------- demo CLI

if __name__ == "__main__":
    import sys, json
    topic = sys.argv[1] if len(sys.argv) > 1 else "spiking neural networks"
    method = sys.argv[2] if len(sys.argv) > 2 else "optimization"
    field = sys.argv[3] if len(sys.argv) > 3 else "neuromorphic computing"

    print(">> FASE 1 — query generate dalle risposte:")
    qs = build_queries(topic, method, field)
    for q in qs:
        print("   -", q)

    print("\n>> FASE 2 — paper seed (2 per query):")
    seeds = get_seed_papers(qs, sort_choice="citations", per_query=2)
    for s in seeds:
        print("   [%s] %s (%s, %s cit.)" % (s["paperId"][:8], s["title"], s["year"], s["citationCount"]))

    # simulo: l'utente sceglie i primi 3 come positivi, gli altri negativi
    pos = [s["paperId"] for s in seeds[:3]]
    neg = [s["paperId"] for s in seeds[3:]]

    print("\n>> FASE 3 — grafo + vettore profilo:")
    g = build_graph_and_profile(pos, neg)
    print("   stats:", json.dumps(g["stats"]))
    print("   vettore profilo: dimensione %d, primi valori %s" %
          (len(g["profileVector"]), [round(x, 3) for x in g["profileVector"][:5]]))
