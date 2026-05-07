"""
pipeline/store.py
Qdrant vector store — production-grade, persistent, supports hybrid search.

Why Qdrant over ChromaDB:
  - Built-in sparse vector support (needed for hybrid BM25+dense search)
  - Much faster ANN search (HNSW index)
  - Payload filtering (filter by source, date, etc.)
  - Production-ready — used at scale by real companies
  - Still runs fully local with no Docker needed (qdrant-client local mode)

WHAT CHANGED FROM ORIGINAL:
  get_client() now checks cfg.QDRANT_URL first.
  If set  → connects to Qdrant Cloud (production / Cloud Run)
  If empty → falls back to local disk via cfg.QDRANT_PATH (offline dev)
  Everything else (upsert, search, scroll) is completely unchanged.
"""
import config as cfg
from qdrant_client import QdrantClient

_client = None
_embedder = None
COLLECTION = "support_docs"


def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(cfg.EMBEDDING_MODEL)
    return _embedder


def get_client() -> QdrantClient:
    """
    Returns a QdrantClient, initialised once and cached globally.

    Decision logic:
      QDRANT_URL set   → Qdrant Cloud  (production)
      QDRANT_URL empty → local disk    (local dev fallback)

    prefer_grpc=True speeds up upserts and searches by ~30% on Qdrant Cloud.
    Has no effect on the local path client (silently ignored).
    timeout=20 ensures Cloud Run doesn't hang on a slow Qdrant response.
    """
    global _client
    if _client is None:
        if cfg.QDRANT_URL:
            # ── Production: Qdrant Cloud ──────────────────────────────────────
            _client = QdrantClient(
                url=cfg.QDRANT_URL,
                api_key=cfg.QDRANT_API_KEY,
                prefer_grpc=True,
                timeout=20,
            )
        else:
            # ── Local dev fallback: on-disk Qdrant ────────────────────────────
            _client = QdrantClient(path=cfg.QDRANT_PATH)

        _ensure_collection()
    return _client


def _ensure_collection():
    """
    Create the Qdrant collection if it doesn't exist yet.
    Safe to call on every startup — no-ops if collection already present.

    WHY NOT recreate_collection():
      That would wipe all vectors on every deploy/restart.
      get_collections() + conditional create is the idempotent pattern.
    """
    from qdrant_client.models import Distance, VectorParams
    client = _client
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=cfg.EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )


def get_all_points() -> list:
    """Return all stored points (used for BM25 index rebuild)."""
    client = get_client()
    points, offset = [], None
    while True:
        batch, offset = client.scroll(
            collection_name=COLLECTION,
            limit=100,
            offset=offset,
            with_vectors=False,
            with_payload=True,
        )
        points.extend(batch)
        if offset is None:
            break
    return points


def get_ingested_sources() -> list[str]:
    """Return unique source filenames in the collection."""
    points = get_all_points()
    return list({p.payload.get("source", "") for p in points if p.payload.get("source")})


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts into dense vectors."""
    embedder = get_embedder()
    return embedder.encode(texts, normalize_embeddings=True).tolist()


def upsert_chunks(chunks: list[dict]):
    """
    Insert chunks into Qdrant.
    Each chunk: {"id": str, "text": str, "source": str, "chunk_index": int}
    """
    import uuid
    from qdrant_client.models import PointStruct

    client = get_client()
    texts = [c["text"] for c in chunks]
    vecs  = embed_texts(texts)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vecs[i],
            payload={
                "text":        chunks[i]["text"],
                "source":      chunks[i]["source"],
                "chunk_index": chunks[i]["chunk_index"],
            },
        )
        for i in range(len(chunks))
    ]
    client.upsert(collection_name=COLLECTION, points=points)


def vector_search(query_vec: list[float], top_k: int) -> list[dict]:
    """Dense vector search. Returns list of {text, source, score}."""
    client = get_client()
    results = client.query_points(
        collection_name=COLLECTION,
        query=query_vec,
        limit=top_k,
        with_payload=True,
    )
    return [
        {"text": h.payload["text"], "source": h.payload["source"], "score": h.score}
        for h in results.points
    ]
