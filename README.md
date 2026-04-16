# RAG Customer Support Chatbot

A production-grade customer support chatbot built with advanced retrieval techniques, hybrid search, conversation memory, and live order tracking — all using free and open-source tools.

---

## Demo

> Ask policy questions, track orders, check return and refund status — all in one interface.

```
You: Where is my order ORD100002?
Bot: Your order ORD100002 (Samsung Galaxy Watch 6) is currently out for delivery
     via DTDC (tracking: DTDC987654IN), expected by April 13. [1]

You: What happens if it doesn't arrive today?
Bot: If your order doesn't arrive on the expected date, you can contact our
     support team via live chat or call 1800-123-4567... [1][2]
```

---

## What makes this different from a basic RAG chatbot

Most RAG demos do: embed documents → vector search → generate answer.

This project adds four production techniques on top of that:

| Technique | What it solves |
|---|---|
| HyDE query rewriting | Raw questions live in "question space", documents live in "answer space" — HyDE bridges the gap by generating a hypothetical answer before embedding |
| Hybrid search (BM25 + dense) | Vector search misses exact keyword matches like product names and IDs; BM25 catches them |
| Reciprocal Rank Fusion | Merges two ranked lists from BM25 and vector search into one without any manual weight tuning |
| Cross-encoder reranking | Bi-encoder retrieval is fast but approximate; cross-encoder scores each (query, chunk) pair together for true relevance |

Plus two things most demos skip entirely:

- **Live database integration** — detects order/return/refund IDs in the user message, queries SQLite, and injects real transactional data into the prompt alongside RAG context
- **Conversation memory** — sliding window of last N turns injected into the system prompt so follow-up questions like "tell me more about that" work correctly

---

## Architecture

```
User message
    │
    ├─► ID detection (regex: ORD / RET / REF)
    │       └─► SQLite query → order + return + refund data
    │
    ├─► HyDE rewrite (LLaMA 3.3 via Groq)
    │       └─► embed hypothetical answer (all-MiniLM-L6-v2)
    │
    ├─► Vector search    ──┐
    │   (Qdrant HNSW)      ├─► RRF merge → Cross-encoder rerank → Top 4 chunks
    ├─► BM25 search     ──┘
    │   (rank-bm25)
    │
    └─► Prompt assembly
            ├── SQLite data block
            ├── RAG context [1][2][3][4]
            └── Conversation memory (last N turns)
                    │
                    └─► LLaMA 3.3 70B (Groq) → SSE stream → Browser
```

---

## Project structure

```
rag-chatbot/
├── chatbot.py              # CLI entry point
├── api.py                  # FastAPI server entry point
│
├── config/
│   └── settings.py         # all config loaded from .env
│
├── pipeline/
│   ├── store.py            # Qdrant client, embed, upsert, vector search
│   ├── ingestion.py        # parse → SHA256 dedup → chunk → embed → store
│   ├── bm25_index.py       # BM25 index built in-memory from Qdrant payloads
│   ├── retriever.py        # HyDE → vector+BM25 → RRF → cross-encoder rerank
│   ├── generator.py        # prompt assembly + streaming (CLI and API modes)
│   └── memory.py           # sliding window conversation memory
│
├── database/
│   ├── schema.py           # SQLite tables: customers, orders, items, returns, refunds
│   ├── seed.py             # sample data (10 orders, 5 returns, 4 refunds)
│   └── queries.py          # ID detection, lookup, and context formatters
│
├── docs/                   # knowledge base documents (PDF, DOCX, TXT)
├── frontend/
│   └── index.html          # single-file browser UI (no npm, no build step)
│
├── requirements.txt
└── .env.example
```

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| LLM | LLaMA 3.3 70B via Groq | Free tier, extremely fast inference |
| Embeddings | all-MiniLM-L6-v2 | Runs locally, no API needed, 384-dim vectors |
| Vector DB | Qdrant | Production-grade HNSW index, payload filtering, runs local |
| Keyword search | BM25 via rank-bm25 | Catches exact matches that vector search misses |
| Reranker | ms-marco-MiniLM-L-6-v2 | Cross-encoder, runs locally, trained on MS MARCO |
| Backend | FastAPI + Uvicorn | Async, SSE streaming, clean routing |
| Database | SQLite | Zero setup, persistent, sufficient for demo scale |
| Document parsing | pypdf + python-docx | Direct parsing, no external services needed |
| Chunking | LangChain text splitters | Recursive character splitting with overlap |

**Total cost to run: ₹0** — all models run locally, Groq has a free tier.

---

## Quick start

### 1. Get a free Groq API key
Sign up at [console.groq.com](https://console.groq.com) — free, no credit card required.

### 2. Clone and install
```bash
git clone https://github.com/YOUR_USERNAME/rag-chatbot.git
cd rag-chatbot
pip install -r requirements.txt
```

### 3. Configure
```bash
cp .env.example .env
# Open .env and add your GROQ_API_KEY
```

### 4. Add your documents
Drop `.txt`, `.pdf`, or `.docx` files into the `docs/` folder. Three sample documents are already included.

### 5. Run

**Browser UI:**
```bash
uvicorn api:app --reload --port 8000
# Open frontend/index.html in your browser
```

**Terminal:**
```bash
python chatbot.py
```

On first run, models load and documents ingest automatically. Subsequent runs skip already-ingested files and start in seconds.

---

## Sample questions to try

**Policy questions (knowledge base):**
```
What is your return policy?
How long does a refund take?
What payment methods do you accept?
What is the warranty on smartphones?
My order shows delivered but I have not received it
```

**Order tracking (live database):**
```
Where is my order ORD100002?
Status of ORD100004
Show me everything about ORD100007
```

**Returns and refunds:**
```
Status of my return RET001
When will I get my refund REF003?
My return RET004 was rejected, what can I do?
```

**Context-aware follow-ups (tests conversation memory):**
```
Turn 1: What is the status of ORD100007?
Turn 2: When is the return pickup scheduled?
Turn 3: How long after pickup will I get the refund?
Turn 4: Which account will the refund go to?
```

---

## Sample data included

| Order ID | Status |
|---|---|
| ORD100001 | Delivered |
| ORD100002 | Out for delivery |
| ORD100003 | Processing |
| ORD100004 | Cancelled |
| ORD100005 | Shipped |
| ORD100007 | Return initiated |
| ORD100008 | Payment failed |

| ID | Type | Status |
|---|---|---|
| RET001 | Return | Pickup scheduled |
| RET002 | Return | Completed |
| RET004 | Return | Rejected |
| REF001 | Refund | Processed — ₹1198 |
| REF003 | Refund | Processing — ₹948 |
| REF004 | Refund | Pending |

---

## How each technique works

### HyDE
```
User:  "How do I reset my password?"
HyDE:  "To reset your password, click Forgot Password on the login
        page and enter your registered email address..."
       → embed this answer, not the raw question
```

### Hybrid search + RRF
```
Vector search  →  [chunk_A rank1, chunk_C rank2, chunk_B rank3 ...]
BM25 search    →  [chunk_B rank1, chunk_A rank2, chunk_D rank3 ...]
RRF formula    →  score = 1/(60+rank_vector) + 1/(60+rank_bm25)
Result         →  chunk_A scores highest (appeared high in both lists)
```

### Database injection
```
User: "Where is ORD100002?"
  → regex detects ORD100002
  → SQLite: orders JOIN customers + order_items + returns + refunds
  → formatted text block injected into LLM prompt
  → LLM answers with real order data + policy context from docs
```

---

## Configuration

All settings via `.env`:

```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
EMBEDDING_MODEL=all-MiniLM-L6-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
DOCS_DIR=./docs
QDRANT_PATH=./qdrant_db
CHUNK_SIZE=512
CHUNK_OVERLAP=64
TOP_K_VECTOR=10
TOP_K_BM25=10
TOP_K_RERANK=4
RRF_K=60
MEMORY_TURNS=6
```

---

## Possible improvements

- GPU support for embeddings and reranking (10x speed)
- Summarization-based memory instead of sliding window
- Query expansion — generate multiple phrasings and retrieve for each
- RAGAS evaluation pipeline to score retrieval precision and answer faithfulness
- User authentication for isolated multi-user sessions
- Deploy to Render with persistent Qdrant volume

---

## Author

**Sushant Sehgal** — AI Engineer  
[LinkedIn](https://linkedin.com/in/YOUR_LINKEDIN) · [GitHub](https://github.com/YOUR_USERNAME)  
sushantsehgal@email.com
