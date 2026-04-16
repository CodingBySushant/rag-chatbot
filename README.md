# RAG Chatbot v3 — CLI

Advanced RAG chatbot with hybrid search, conversation memory, and duplicate detection.

## What's new vs v2

| Feature | v2 | v3 |
|---|---|---|
| Vector DB | ChromaDB | Qdrant (faster, production-grade) |
| Search | Dense only | Hybrid: BM25 + dense, merged with RRF |
| Memory | None | Sliding window (last N turns) |
| Duplicate detection | Filename only | SHA256 content hash |

## Project structure

```
rag-chatbot-v3/
├── chatbot.py              # CLI entry point — I/O and chat loop only
├── config/
│   ├── __init__.py
│   └── settings.py         # all config from .env
├── pipeline/
│   ├── __init__.py
│   ├── store.py            # Qdrant client + embed + upsert + search
│   ├── deduplication.py    # SHA256 hash tracking (ingested_hashes.json)
│   ├── ingestion.py        # parse → chunk → dedup → upsert
│   ├── bm25_index.py       # BM25 keyword index (rebuilt in-memory at startup)
│   ├── retriever.py        # HyDE → vector + BM25 → RRF → rerank
│   ├── memory.py           # sliding window conversation memory
│   └── generator.py        # prompt + streaming LLM answer
├── docs/                   # drop documents here
├── qdrant_db/              # created automatically (Qdrant storage)
├── ingested_hashes.json    # created automatically (dedup tracking)
├── requirements.txt
└── .env.example
```

## Setup

```bash
pip install -r requirements.txt
copy .env.example .env      # Windows
# cp .env.example .env      # Mac/Linux
# Edit .env — add your GROQ_API_KEY (free at console.groq.com)
python chatbot.py
```

## Commands

| Command | Action |
|---|---|
| `memory` | Show conversation history |
| `clear memory` | Reset conversation memory |
| `sources` | List ingested documents |
| `clear` | Clear the terminal |
| `quit` | Exit |

## How hybrid search works

1. Your question is rewritten via HyDE into a hypothetical answer
2. The hypothetical answer is embedded and searched in Qdrant (dense, top-10)
3. Your original question is searched via BM25 keywords (sparse, top-10)
4. Both ranked lists are merged using Reciprocal Rank Fusion (RRF)
5. The merged list is re-scored by a cross-encoder, top-4 kept
6. LLaMA 3.3 generates a streamed answer with source citations

## How duplicate detection works

Every file gets SHA256-hashed before ingestion.
The hash is stored in `ingested_hashes.json`.
On next run, if the hash already exists — skip.
If you update a file's content, it gets a new hash and re-ingests automatically.
