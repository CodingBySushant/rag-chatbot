"""
chatbot.py — CLI entry point
Handles terminal I/O and the chat loop only.
All RAG logic lives in pipeline/.
"""
import os
import sys
import config as cfg
from pipeline import (
    ingest_docs, get_ingested_sources, get_client,
    retrieve, get_reranker, build_bm25_index,
    ConversationMemory, stream_answer,
)
from pipeline.store import get_embedder


# ── Colors ────────────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    CYAN   = "\033[36m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    RED    = "\033[31m"
    DIM    = "\033[2m"


def banner():
    print(f"""
{C.CYAN}{C.BOLD}
  ██████╗  █████╗  ██████╗     ██████╗██╗  ██╗ █████╗ ████████╗
  ██╔══██╗██╔══██╗██╔════╝    ██╔════╝██║  ██║██╔══██╗╚══██╔══╝
  ██████╔╝███████║██║  ███╗   ██║     ███████║███████║   ██║
  ██╔══██╗██╔══██║██║   ██║   ██║     ██╔══██║██╔══██║   ██║
  ██║  ██║██║  ██║╚██████╔╝   ╚██████╗██║  ██║██║  ██║   ██║
  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝
{C.RESET}
  {C.DIM}Hybrid Search · HyDE · Rerank · Memory · Qdrant · LLaMA 3.3{C.RESET}
""")


# ── Per-query flow ────────────────────────────────────────────────────────────

def run_query(question: str, memory: ConversationMemory):
    # Step 1: HyDE + hybrid retrieval
    print(f"\n  {C.DIM}[1/3] HyDE + hybrid search (vector + BM25)...{C.RESET}", end="\r")
    chunks, hyde_query = retrieve(question)
    print(f"  {C.DIM}[1/3] HyDE:{C.RESET} {hyde_query[:80].strip()}{'...' if len(hyde_query) > 80 else ''}")
    print(f"  {C.DIM}[2/3] Retrieved {len(chunks)} chunks via RRF + rerank.{C.RESET}  ")

    if not chunks:
        print(f"\n  {C.RED}No relevant documents found.{C.RESET}\n")
        return None

    # Show sources
    print(f"\n  {C.YELLOW}── Sources ─────────────────────────────────────────{C.RESET}")
    for i, chunk in enumerate(chunks, start=1):
        source  = chunk.get("source", "unknown")
        snippet = chunk["text"].strip()[:100].replace("\n", " ")
        score   = chunk.get("rerank_score", 0)
        print(f"  {C.DIM}[{i}] {source}  (rerank: {score:.3f}){C.RESET}")
        print(f"      {C.DIM}{snippet}...{C.RESET}")

    # Stream answer (with conversation memory context)
    print(f"\n  {C.CYAN}── Answer ───────────────────────────────────────────{C.RESET}")
    print(f"  {C.BOLD}", end="", flush=True)

    memory_block = memory.format_for_prompt()
    _, full_answer = stream_answer(question, chunks, memory_block)

    print(C.RESET)
    return full_answer


# ── Startup ───────────────────────────────────────────────────────────────────

def startup():
    if not cfg.GROQ_API_KEY:
        print(f"\n  {C.RED}ERROR: GROQ_API_KEY not set.{C.RESET}")
        print(f"  Add to .env:  GROQ_API_KEY=gsk_...\n")
        sys.exit(1)

    banner()

    # Auto-ingest docs
    print(f"  {C.CYAN}Checking knowledge base...{C.RESET}")
    ingest_docs(verbose=True)

    # Pre-warm all models
    print(f"  {C.DIM}Loading models...{C.RESET}", end="\r")
    get_client()
    get_embedder()
    get_reranker()
    build_bm25_index()   # build BM25 index from all Qdrant payloads
    print(f"  {C.GREEN}✓{C.RESET} All models ready.              ")

    # Show loaded sources
    sources = get_ingested_sources()
    if sources:
        print(f"\n  {C.GREEN}Knowledge base:{C.RESET} {len(sources)} document(s)")
        for s in sorted(sources):
            print(f"    {C.DIM}• {s}{C.RESET}")
    else:
        print(f"\n  {C.YELLOW}No documents loaded. Add files to ./docs/ and restart.{C.RESET}")

    print(f"\n  {C.DIM}Commands: 'memory' · 'clear memory' · 'sources' · 'clear' · 'quit'{C.RESET}")
    print(f"  {C.DIM}{'─' * 54}{C.RESET}\n")


# ── Chat loop ─────────────────────────────────────────────────────────────────

def chat_loop():
    memory = ConversationMemory(max_turns=cfg.MEMORY_TURNS)

    while True:
        try:
            # Show memory indicator if active
            mem_tag = f" {C.DIM}[mem:{memory.turn_count()}]{C.RESET}" if not memory.is_empty() else ""
            user_input = input(f"{C.CYAN}{C.BOLD}You{mem_tag}{C.CYAN}{C.BOLD}:{C.RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n  {C.DIM}Goodbye!{C.RESET}\n")
            break

        if not user_input:
            continue

        match user_input.lower():
            case "quit" | "exit" | "q":
                print(f"\n  {C.DIM}Goodbye!{C.RESET}\n")
                break

            case "memory":
                if memory.is_empty():
                    print(f"\n  {C.DIM}No conversation history yet.{C.RESET}\n")
                else:
                    print(f"\n  {C.YELLOW}── Conversation memory ({memory.turn_count()} turns) ──{C.RESET}")
                    for turn in memory.get_history():
                        prefix = f"{C.CYAN}You{C.RESET}" if turn["role"] == "user" else f"{C.GREEN}Bot{C.RESET}"
                        print(f"  {prefix}: {turn['content'][:120]}")
                    print()

            case "clear memory":
                memory.clear()
                print(f"\n  {C.GREEN}Memory cleared.{C.RESET}\n")

            case "sources":
                sources = get_ingested_sources()
                print(f"\n  {C.GREEN}Loaded documents:{C.RESET}")
                for s in sorted(sources):
                    print(f"    • {s}")
                print()

            case "clear":
                os.system("cls" if os.name == "nt" else "clear")
                banner()

            case _:
                print(f"\n{C.BOLD}  Assistant:{C.RESET}")
                answer = run_query(user_input, memory)
                if answer:
                    # Store this turn in memory
                    memory.add("user",      user_input)
                    memory.add("assistant", answer)


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    startup()
    chat_loop()
