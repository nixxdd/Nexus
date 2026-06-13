# -*- coding: utf-8 -*-
"""
Client Semantic Scholar in pura libreria standard (urllib).
Gestisce: rate limiting (~1 req/sec con chiave), retry su 429/5xx, header con API key.
"""
import json
import time
import urllib.request
import urllib.parse
import urllib.error

import config

_last_call = [0.0]

def _throttle():
    """Rispetta il limite di ~1 richiesta al secondo imposto da Semantic Scholar."""
    dt = time.time() - _last_call[0]
    if dt < config.RATE_DELAY:
        time.sleep(config.RATE_DELAY - dt)
    _last_call[0] = time.time()

def _headers(json_body=False):
    h = {"User-Agent": "NEXUS-HackRome/1.0"}
    if config.S2_API_KEY:
        h["x-api-key"] = config.S2_API_KEY
    if json_body:
        h["Content-Type"] = "application/json"
    return h

def _request(url, params=None, body=None, retries=4):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    for attempt in range(retries):
        _throttle()
        try:
            req = urllib.request.Request(url, data=data, headers=_headers(json_body=body is not None))
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # 429 = troppe richieste, 5xx = errore server temporaneo -> riprova con backoff
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue
            detail = ""
            try:
                detail = e.read().decode("utf-8")[:300]
            except Exception:
                pass
            raise RuntimeError("Semantic Scholar HTTP %s su %s : %s" % (e.code, url, detail))
        except urllib.error.URLError as e:
            if attempt < retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise RuntimeError("Errore di rete verso Semantic Scholar: %s" % e)
    raise RuntimeError("Richiesta fallita dopo %d tentativi: %s" % (retries, url))

# ---------------------------------------------------------------- endpoint

def search_bulk(query, sort="citationCount:desc", limit=10,
                fields="title,year,authors,citationCount,abstract,externalIds"):
    """
    Cerca paper per testo (endpoint /paper/search/bulk).
    'sort' puo' essere 'citationCount:desc' oppure 'publicationDate:desc'.
    Ritorna la lista dei paper (gia' troncata a 'limit').
    """
    params = {"query": query, "fields": fields}
    if sort:
        params["sort"] = sort
    res = _request(config.SEARCH_BULK_URL, params=params)
    data = res.get("data") or []
    return data[:limit]

def get_papers_batch(ids,
                     fields="title,year,authors,citationCount,embedding,references.paperId,externalIds,abstract"):
    """
    Recupera in un colpo solo i dettagli (inclusi gli embedding SPECTER) di piu' paper
    (endpoint /paper/batch, max 500 id). Ritorna lista allineata agli id (None se mancante).
    """
    ids = [i for i in ids if i]
    if not ids:
        return []
    out = []
    # il batch accetta fino a 500 id; spezzo per sicurezza
    for k in range(0, len(ids), 400):
        chunk = ids[k:k + 400]
        res = _request(config.PAPER_BATCH_URL, params={"fields": fields}, body={"ids": chunk})
        if isinstance(res, list):
            out.extend(res)
    return out

def recommend(positive_ids, negative_ids=None,
              fields="title,year,authors,citationCount,externalIds", limit=40):
    """
    Espande il grafo: dati i paper 'positivi' (scelti dall'utente) e 'negativi'
    (scartati / gia' presenti), ritorna i paper raccomandati (endpoint /recommendations).
    """
    body = {"positivePaperIds": list(positive_ids or [])}
    if negative_ids:
        body["negativePaperIds"] = list(negative_ids)
    params = {"fields": fields, "limit": str(limit)}
    res = _request(config.REC_URL, params=params, body=body)
    return res.get("recommendedPapers") or []
