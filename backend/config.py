# -*- coding: utf-8 -*-
"""Configurazione centrale: legge il file .env e definisce gli endpoint Semantic Scholar."""
import os

def _load_env():
    """Mini-parser di .env (cosi' non serve installare python-dotenv)."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, ".env")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

_load_env()

S2_API_KEY = os.environ.get("S2_API_KEY", "").strip()
RATE_DELAY = float(os.environ.get("S2_RATE_DELAY", "1.1"))
CURRENT_YEAR = int(os.environ.get("NEXUS_CURRENT_YEAR", "2026"))

# endpoint (https — sempre cifrato)
GRAPH_BASE = "https://api.semanticscholar.org/graph/v1"
SEARCH_BULK_URL = GRAPH_BASE + "/paper/search/bulk"
PAPER_BATCH_URL = GRAPH_BASE + "/paper/batch"
REC_URL = "https://api.semanticscholar.org/recommendations/v1/papers"

# coefficienti della formula dei pesi degli archi (dal brief):
# peso = 0.5*coseno + 0.3*co-citazione + 0.15*citazione_diretta + 0.05*feedback
W_COSINE = 0.50
W_COCITE = 0.30
W_DIRECT = 0.15
W_FEEDBACK = 0.05

# soglia minima per tenere un arco nel grafo
EDGE_THRESHOLD = 0.30
