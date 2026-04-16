"""
pipeline/ingestion.py
Full ingestion pipeline:
  1. Scan ./docs/ for supported files
  2. Hash each file — skip if already ingested (duplicate detection)
  3. Parse to plain text (PDF / DOCX / TXT / MD)
  4. Split into overlapping chunks
  5. Upsert chunks into Qdrant
  6. Register hash so file is never re-ingested
"""
from pathlib import Path
import config as cfg
from pipeline.store import upsert_chunks
from pipeline.deduplication import compute_hash, is_duplicate, register_hash, remove_hash

SUPPORTED = {".txt", ".md", ".pdf", ".docx"}


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return "\n\n".join(p.extract_text() for p in reader.pages if p.extract_text())


def _parse_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _parse_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":   return _parse_pdf(path)
    if ext == ".docx":  return _parse_docx(path)
    if ext in (".txt", ".md"): return _parse_txt(path)
    return ""


# ── Chunking ──────────────────────────────────────────────────────────────────

def split_text(text: str, source: str) -> list[dict]:
    """Split text into overlapping chunks. Returns list of chunk dicts."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.CHUNK_SIZE,
        chunk_overlap=cfg.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    parts = splitter.split_text(text)
    return [
        {"text": part, "source": source, "chunk_index": i}
        for i, part in enumerate(parts)
        if part.strip()
    ]


# ── Main ingestion entry point ────────────────────────────────────────────────

def ingest_docs(verbose: bool = True) -> int:
    """
    Scan DOCS_DIR and ingest new files.
    Skips duplicates using SHA256 content hash.
    Returns total number of new chunks added.
    """
    docs_path = Path(cfg.DOCS_DIR)

    if not docs_path.exists():
        docs_path.mkdir(parents=True)
        if verbose:
            print("  Created ./docs/ — add your documents and restart.")
        return 0

    files = [
        f for f in docs_path.glob("**/*")
        if f.is_file() and f.suffix.lower() in SUPPORTED
    ]

    if not files:
        if verbose:
            print("  ./docs/ is empty — add .txt/.pdf/.docx files and restart.")
        return 0

    total_chunks  = 0
    skipped       = 0
    newly_ingested = 0

    for fp in files:
        raw_bytes  = fp.read_bytes()
        file_hash  = compute_hash(raw_bytes)

        # ── Duplicate detection ───────────────────────────────────────────────
        if is_duplicate(file_hash):
            skipped += 1
            if verbose:
                print(f"  {fp.name}  →  skipped (already ingested)")
            continue

        # ── Parse ─────────────────────────────────────────────────────────────
        text = parse_file(fp)
        if not text.strip():
            if verbose:
                print(f"  {fp.name}  →  skipped (empty after parsing)")
            continue

        # ── Chunk + upsert ────────────────────────────────────────────────────
        chunks = split_text(text, source=fp.name)
        try:
            upsert_chunks(chunks)
            register_hash(file_hash, fp.name)   # only register on success
            total_chunks   += len(chunks)
            newly_ingested += 1
            if verbose:
                print(f"  ✓  {fp.name}  →  {len(chunks)} chunks")
        except Exception as e:
            if verbose:
                print(f"  ✗  {fp.name}  →  failed: {e}")

    if verbose:
        if newly_ingested == 0 and skipped > 0:
            print(f"  All {skipped} file(s) already in knowledge base — nothing to do.")
        elif newly_ingested > 0:
            print(f"  Done — {total_chunks} new chunks from {newly_ingested} file(s).")
            if skipped:
                print(f"  ({skipped} duplicate(s) skipped)")
        print()

    return total_chunks
