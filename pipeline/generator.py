"""
pipeline/generator.py
Builds the final prompt and streams the answer.

Prompt sections (in order):
  1. Instructions
  2. Order details  (injected when user mentions an order ID)
  3. RAG context    (top retrieved chunks)
  4. Memory         (last N conversation turns)
"""
import config as cfg


RAG_SYSTEM = """\
You are a helpful customer support assistant for ACME Store.
Answer using the information provided below (order details and/or knowledge base context).
Cite knowledge base sources inline like [1] or [2] when used.
If you don't have enough information, say so honestly — do not make things up.
Be concise, clear, and friendly.

{order_block}
{context_block}
{memory_block}\
"""


def _build_context(chunks: list[dict]) -> tuple[str, list[dict]]:
    parts     = []
    citations = []
    for i, chunk in enumerate(chunks, start=1):
        source  = chunk.get("source", "unknown")
        text    = chunk["text"].strip()
        parts.append(f"[{i}] Source: {source}\n{text}")
        citations.append({
            "index":   i,
            "source":  source,
            "snippet": text[:150] + ("..." if len(text) > 150 else ""),
            "score":   round(chunk.get("rerank_score", 0), 4),
        })
    return "\n\n".join(parts), citations


def _make_chain(order_block: str, context_block: str, memory_block: str):
    from langchain_groq import ChatGroq
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    llm = ChatGroq(
        api_key=cfg.GROQ_API_KEY,
        model=cfg.GROQ_MODEL,
        temperature=cfg.LLM_TEMPERATURE,
        streaming=True,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", RAG_SYSTEM),
        ("human",  "{question}"),
    ])
    return prompt | llm | StrOutputParser(), {
        "order_block":  f"--- Order Information ---\n{order_block}\n" if order_block  else "",
        "context_block": f"--- Knowledge Base ---\n{context_block}\n" if context_block else "",
        "memory_block":  f"--- Conversation History ---\n{memory_block}\n" if memory_block else "",
    }


def stream_answer(
    question:     str,
    chunks:       list[dict],
    memory_block: str = "",
    order_block:  str = "",
) -> tuple[list[dict], str]:
    """CLI mode — stream tokens to stdout."""
    context_str, citations = _build_context(chunks)
    chain, blocks = _make_chain(order_block, context_str, memory_block)

    full_answer = ""
    for token in chain.stream({"question": question, **blocks}):
        print(token, end="", flush=True)
        full_answer += token

    print()
    return citations, full_answer


def stream_answer_api(
    question:     str,
    chunks:       list[dict],
    memory_block: str = "",
    order_block:  str = "",
):
    """API mode — yields SSE strings for FastAPI StreamingResponse."""
    import json

    context_str, citations = _build_context(chunks)
    chain, blocks = _make_chain(order_block, context_str, memory_block)

    yield f"data: {json.dumps({'type': 'citations', 'data': citations})}\n\n"

    for token in chain.stream({"question": question, **blocks}):
        yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"
