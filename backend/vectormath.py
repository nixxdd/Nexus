# -*- coding: utf-8 -*-
"""Operazioni sui vettori in puro Python (niente numpy, zero dipendenze)."""
import math

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))

def norm(a):
    return math.sqrt(sum(x * x for x in a))

def cosine(a, b):
    """Similarita' coseno tra due embedding (1 = identici, 0 = ortogonali)."""
    if not a or not b:
        return 0.0
    na, nb = norm(a), norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return dot(a, b) / (na * nb)

def euclidean(a, b):
    if not a or not b:
        return 0.0
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

def mean_vector(vectors, weights=None):
    """Media (eventualmente pesata) di una lista di vettori della stessa dimensione."""
    vectors = [v for v in vectors if v]
    if not vectors:
        return []
    dim = len(vectors[0])
    if weights is None:
        weights = [1.0] * len(vectors)
    acc = [0.0] * dim
    wsum = 0.0
    for v, w in zip(vectors, weights):
        if not v or len(v) != dim:
            continue
        for i in range(dim):
            acc[i] += v[i] * w
        wsum += w
    if wsum == 0:
        return acc
    return [x / wsum for x in acc]

def jaccard(set_a, set_b):
    """Indice di Jaccard tra due insiemi (per la co-citazione = riferimenti condivisi)."""
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union else 0.0
