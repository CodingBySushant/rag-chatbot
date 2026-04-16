"""
pipeline/retriever.py
Full hybrid retrieval pipeline:

  1. HyDE    — rewrite query as hypothetical answer for better embedding alignment
  2. Vector  — dense semantic search via Qdrant (top-K)
  3. BM25    — sparse keyword search (top-K)
  4. RRF     — Reciprocal Rank Fusion merges both ranked lists into one
  5. Rerank  — cross-encoder scores merged candidates for final precision

Why RRF:
  Simple formula: score(d) = Σ 1/(k + rank(d))
  It rewards documents that appear high in BOTH lists.
  No tuning needed — k=60 is the standard default.
"""
import config as cfg
from pipeline.store import embed_texts, vector_search
from pipeline.bm25_index import bm25_search

_reranker = None


def get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(cfg.RERANKER_MODEL)
    return _reranker


# ── HyDE ─────────────────────────────────────────────────────────────────────

def hyde_rewrite(question: str) -> str:
    """Generate a hypothetical answer to embed instead of the raw question."""
    from langchain_groq import ChatGroq
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    llm = ChatGroq(
        api_key=cfg.GROQ_API_KEY,
        model=cfg.GROQ_MODEL,
        temperature=cfg.LLM_TEMPERATURE,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a customer support agent. Write a short 2-3 sentence answer "
         "to the following question as if it appeared in a support FAQ document. "
         "Always give a direct, plausible answer."),
        ("human", "{question}"),
    ])
    return (prompt | llm | StrOutputParser()).invoke({"question": question})


# ── Reciprocal Rank Fusion ────────────────────────────────────────────────────

def reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results:   list[dict],
    k: int = None,
) -> list[dict]:
    """
    Merge two ranked lists using RRF.
    Returns deduplicated list sorted by combined RRF score (descending).
    """
    k = k or cfg.RRF_K
    scores: dict[str, float] = {}
    docs:   dict[str, dict]  = {}

    for rank, doc in enumerate(vector_results):
        key = doc["text"][:120]   # use text prefix as key
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        docs[key]   = doc

    for rank, doc in enumerate(bm25_results):
        key = doc["text"][:120]
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        docs[key]   = doc

    merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [
        {**docs[key], "rrf_score": rrf_score}
        for key, rrf_score in merged
    ]


# ── Cross-encoder reranker ────────────────────────────────────────────────────

def rerank(query: str, candidates: list[dict], top_k: int = None) -> list[dict]:
    """Score each (query, chunk) pair with cross-encoder. Return top_k."""
    top_k = top_k or cfg.TOP_K_RERANK
    if not candidates:
        return []

    model  = get_reranker()
    pairs  = [[query, c["text"]] for c in candidates]
    scores = model.predict(pairs)

    reranked = sorted(
        [{**candidates[i], "rerank_score": float(scores[i])} for i in range(len(candidates))],
        key=lambda x: x["rerank_score"],
        reverse=True,
    )
    return reranked[:top_k]


# ── Full pipeline ─────────────────────────────────────────────────────────────

def retrieve(question: str) -> tuple[list[dict], str]:
    """
    Full retrieval:  HyDE → vector + BM25 → RRF → rerank
    Returns (top_chunks, hyde_query_used)
    """
    # Step 1: HyDE
    hyde_query = hyde_rewrite(question)

    # Step 2a: Dense vector search
    query_vec    = embed_texts([hyde_query])[0]
    vector_hits  = vector_search(query_vec, top_k=cfg.TOP_K_VECTOR)

    # Step 2b: BM25 keyword search on original question (not HyDE)
    bm25_hits = bm25_search(question, top_k=cfg.TOP_K_BM25)

    # Step 3: RRF merge
    merged = reciprocal_rank_fusion(vector_hits, bm25_hits)

    # Step 4: Cross-encoder rerank on merged set
    top_chunks = rerank(question, merged, top_k=cfg.TOP_K_RERANK)

    return top_chunks, hyde_query
