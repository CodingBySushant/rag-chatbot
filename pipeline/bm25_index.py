"""
pipeline/bm25_index.py
BM25 keyword search over all ingested chunks.

Why BM25 alongside vector search:
  - Vector search is great for semantic similarity ("how do I get a refund")
  - BM25 is great for exact keyword matches ("ACME Protection Plan", "IP67", "Net30")
  - Hybrid = both signals merged → better coverage than either alone

The BM25 index is rebuilt in-memory at startup from all Qdrant payloads.
It does NOT persist to disk (fast to rebuild, avoids stale index).
"""
from __future__ import annotations
from pipeline.store import get_all_points

_bm25_index = None
_bm25_corpus: list[dict] = []   # [{text, source}, ...]


def build_index():
    """Load all chunks from Qdrant and build a fresh BM25 index."""
    global _bm25_index, _bm25_corpus
    from rank_bm25 import BM25Okapi

    points = get_all_points()
    _bm25_corpus = [
        {"text": p.payload["text"], "source": p.payload.get("source", "")}
        for p in points
        if p.payload.get("text")
    ]

    if not _bm25_corpus:
        _bm25_index = None
        return

    tokenized = [doc["text"].lower().split() for doc in _bm25_corpus]
    _bm25_index = BM25Okapi(tokenized)


def get_index():
    global _bm25_index
    if _bm25_index is None:
        build_index()
    return _bm25_index


def bm25_search(query: str, top_k: int) -> list[dict]:
    """
    BM25 keyword search.
    Returns list of {text, source, score} sorted by BM25 score descending.
    """
    index = get_index()
    if index is None or not _bm25_corpus:
        return []

    tokenized_query = query.lower().split()
    scores = index.get_scores(tokenized_query)

    ranked = sorted(
        enumerate(scores),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    return [
        {
            "text":   _bm25_corpus[i]["text"],
            "source": _bm25_corpus[i]["source"],
            "score":  float(s),
        }
        for i, s in ranked
        if s > 0  # skip zero-score results
    ]
