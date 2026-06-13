# -*- coding: utf-8 -*-
"""
FASE 1 — Onboarding -> query.
Dalle 3 risposte dell'utente (topic specifico, approccio/metodo, campo) costruisce
3 query per Semantic Scholar, che l'utente potra' poi modificare.

NB: qui la logica e' deterministica (combinazioni topic+metodo / topic+campo / metodo+campo).
Se in futuro volete usare un LLM (Claude/Groq) per estrarre query piu' "intelligenti",
basta sostituire build_queries() con una chiamata all'LLM che ritorna 3 stringhe.
"""

def _clean(s):
    return (s or "").strip()

def build_queries(topic, method, field):
    topic, method, field = _clean(topic), _clean(method), _clean(field)
    candidates = []
    if topic and method:
        candidates.append(topic + " " + method)
    if topic and field:
        candidates.append(topic + " " + field)
    if method and field:
        candidates.append(method + " " + field)
    # fallback se l'utente ha compilato poco
    full = " ".join(x for x in [topic, method, field] if x)
    for extra in [full, topic, field, method]:
        candidates.append(extra)

    queries = []
    for q in candidates:
        q = _clean(q)
        if q and q not in queries:
            queries.append(q)
        if len(queries) == 3:
            break
    # se proprio non c'e' nulla, evita lista vuota
    if not queries and full:
        queries = [full]
    return queries[:3]

def sort_param(sort_choice):
    """Mappa la scelta dell'utente sul parametro 'sort' di Semantic Scholar."""
    s = (sort_choice or "citations").lower()
    if s in ("year", "anno", "date", "recent", "recenti"):
        return "publicationDate:desc"
    if s in ("mixed", "alternati", "alternato", "alt"):
        return "MIXED"  # gestito a parte (interleave citazioni + anno)
    return "citationCount:desc"
