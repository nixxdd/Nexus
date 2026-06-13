# NEXUS — Backend

Pipeline reale su **Semantic Scholar**: dal testo dell'onboarding fino al **vettore profilo** dell'utente.
Scritto in **pura libreria standard Python 3** — nessun `pip install`, niente numpy.

## Le 3 fasi

1. **Onboarding → query** (`query_builder.py`)
   Dalle 3 risposte (topic specifico, approccio/metodo, campo) genera **3 query** modificabili.

2. **Query → paper seed** (`pipeline.get_seed_papers`)
   Per ogni query prende **2 paper** (ordinati per citazioni / anno / alternati) da mostrare come card.
   L'utente sceglie i rilevanti → diventano **positivi**; i non scelti → **negativi**.

3. **Paper scelti → grafo + profilo** (`pipeline.build_graph_and_profile`)
   - chiama la **Recommendations API** (positivi + negativi) per espandere il campo;
   - scarica gli **embedding SPECTER** dei nodi (endpoint `/paper/batch`, una sola chiamata);
   - costruisce gli **archi pesati**:
     `peso = 0.5·coseno + 0.3·co-citazione + 0.15·citazione_diretta + 0.05·feedback`;
   - calcola il **VETTORE PROFILO** = media pesata (per recency) degli embedding dei paper scelti.

   > L'agente RAG finale **non** è qui: resta lato interfaccia, come da specifica.

## Setup

1. La chiave sta in `.env` (già presente, **ignorata da git**). Per cambiarla, modifica `S2_API_KEY`.
2. Non serve installare nulla.

## Come si usa

```bash
# pipeline completa in console (query -> seed -> grafo -> profilo)
python pipeline.py "spiking neural networks" "optimization" "neuromorphic computing"

# esporta dati REALI per il globo del frontend
python export_demo.py "spiking neural networks" "optimization" "neuromorphic computing"
#   -> crea backend/out/graph.json  e  backend/out/nexus_real.json

# server live (facoltativo) per collegare il frontend in tempo reale
python server.py        # http://localhost:8000
```

## Collegamento al frontend — due strade

- **(consigliata per il pitch) Pre-cottura.** Lanci `export_demo.py`, ottieni `nexus_real.json`,
  e il globo lo carica come dati. Risultato: **dati 100% reali** ma demo **veloce e offline-safe**
  (niente latenza né rate-limit sul palco).
- **Live.** Avvii `server.py` e il frontend chiama `POST /api/queries → /api/seed → /api/graph`
  via `fetch`. Più "vero", ma reintroduce latenza (4–6s) e dipendenza dalla rete: tieni sempre
  pronto il fallback pre-cotto.

## File

| file | ruolo |
|------|-------|
| `config.py` | legge `.env`, endpoint, coefficienti dei pesi |
| `s2_client.py` | client Semantic Scholar (rate-limit + retry) |
| `query_builder.py` | onboarding → 3 query |
| `vectormath.py` | coseno / media pesata / Jaccard in puro Python |
| `pipeline.py` | seed → recommendations → grafo + vettore profilo |
| `export_demo.py` | esporta JSON reali per il globo (con clustering k-means) |
| `server.py` | mini-API HTTP (stdlib) per la modalità live |

## Nota sicurezza
La chiave Semantic Scholar è nel piano gratuito accademico. Sta in `.env` (fuori dal codice, fuori da git).
Se vuoi, rigenerala su semanticscholar.org: il backend la rilegge dall'ambiente senza toccare il codice.
