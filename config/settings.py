"""
config/settings.py
All configuration loaded from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM ───────────────────────────────────────────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL      = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# ── Models (local, free) ──────────────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RERANKER_MODEL  = os.getenv("RERANKER_MODEL",  "cross-encoder/ms-marco-MiniLM-L-6-v2")
EMBEDDING_DIM   = int(os.getenv("EMBEDDING_DIM", "384"))   # must match model output

# ── Paths ─────────────────────────────────────────────────────────────────────
QDRANT_URL     = os.getenv("QDRANT_URL",     "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
# QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant_db")      # local on-disk Qdrant
DOCS_DIR    = os.getenv("DOCS_DIR",    "./docs")
HASH_FILE   = os.getenv("HASH_FILE",   "./ingested_hashes.json")  # duplicate tracking

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE",    "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "64"))

# ── Retrieval ─────────────────────────────────────────────────────────────────
TOP_K_VECTOR   = int(os.getenv("TOP_K_VECTOR",   "10"))  # candidates from vector search
TOP_K_BM25     = int(os.getenv("TOP_K_BM25",     "10"))  # candidates from BM25
TOP_K_RERANK   = int(os.getenv("TOP_K_RERANK",   "4"))   # kept after cross-encoder rerank
RRF_K          = int(os.getenv("RRF_K",          "60"))  # RRF constant (higher = smoother)

# ── Conversation memory ───────────────────────────────────────────────────────
MEMORY_TURNS = int(os.getenv("MEMORY_TURNS", "6"))  # number of past turns to include
