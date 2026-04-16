"""
api.py — FastAPI server
Run: uvicorn api:app --reload --port 8000
"""
import sys, os, json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))

import config as cfg
from pipeline import (
    ingest_docs, get_ingested_sources, get_client,
    retrieve, get_reranker, build_bm25_index, ConversationMemory,
)
from pipeline.store import get_embedder
from pipeline.generator import stream_answer_api
from database.schema import create_tables
from database.queries import (
    extract_order_id, extract_return_id, extract_refund_id,
    get_order, get_return, get_refund,
    format_order_context, format_return_context, format_refund_context,
)
from database.seed import seed as seed_db

# ── Session memory ────────────────────────────────────────────────────────────
_sessions: dict[str, ConversationMemory] = {}

def get_session(sid: str) -> ConversationMemory:
    if sid not in _sessions:
        _sessions[sid] = ConversationMemory(max_turns=cfg.MEMORY_TURNS)
    return _sessions[sid]

# ── Startup ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("  Setting up database...")
    create_tables()
    seed_db()
    print("  Loading knowledge base...")
    ingest_docs(verbose=True)
    get_client()
    get_embedder()
    get_reranker()
    build_bm25_index()
    print("  Ready.")
    yield

app = FastAPI(title="RAG Chatbot API", version="3.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Models ────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question:   str
    session_id: str = "default"

class ClearMemoryRequest(BaseModel):
    session_id: str = "default"

# ── Helpers ───────────────────────────────────────────────────────────────────
def resolve_db_context(question: str) -> tuple[str, str | None, str | None]:
    """
    Detect any ID in the question and return (context_block, entity_type, entity_id).
    Priority: refund > return > order (most specific first)
    """
    # Refund ID
    rid = extract_refund_id(question)
    if rid:
        rec = get_refund(rid)
        if rec:
            return format_refund_context(rec), "refund", rid
        return "", "refund_not_found", rid

    # Return ID
    ret_id = extract_return_id(question)
    if ret_id:
        rec = get_return(ret_id)
        if rec:
            return format_return_context(rec), "return", ret_id
        return "", "return_not_found", ret_id

    # Order ID
    oid = extract_order_id(question)
    if oid:
        rec = get_order(oid)
        if rec:
            return format_order_context(rec), "order", oid
        return "", "order_not_found", oid

    return "", None, None

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "model": cfg.GROQ_MODEL}

@app.get("/sources")
def sources():
    return {"sources": sorted(get_ingested_sources())}

@app.post("/chat")
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    memory = get_session(req.session_id)

    def generate():
        try:
            # ── Resolve any DB entity from the question ───────────────────────
            db_block, entity_type, entity_id = resolve_db_context(req.question)

            if entity_type and entity_id:
                if entity_type.endswith("_not_found"):
                    yield f"data: {json.dumps({'type': entity_type, 'data': entity_id})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': entity_type + '_found', 'data': entity_id})}\n\n"

            # ── RAG retrieval ─────────────────────────────────────────────────
            chunks, _ = retrieve(req.question)

            if not chunks and not db_block:
                yield f"data: {json.dumps({'type': 'error', 'data': 'No relevant information found.'})}\n\n"
                return

            # ── Stream answer ─────────────────────────────────────────────────
            full_answer = ""
            for event in stream_answer_api(
                req.question, chunks,
                memory_block=memory.format_for_prompt(),
                order_block=db_block,
            ):
                try:
                    parsed = json.loads(event.replace("data: ", "").strip())
                    if parsed["type"] == "token":
                        full_answer += parsed["data"]
                except Exception:
                    pass
                yield event

            if full_answer:
                memory.add("user",      req.question)
                memory.add("assistant", full_answer)

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.post("/memory/clear")
def clear_memory(req: ClearMemoryRequest):
    if req.session_id in _sessions:
        _sessions[req.session_id].clear()
    return {"status": "cleared"}

# ── Serve frontend ────────────────────────────────────────────────────────────
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
