"""
pipeline/deduplication.py
Tracks ingested files by SHA256 hash of their content.

Why SHA256 and not just filename:
  - Filename can be the same but content different (updated FAQ doc)
  - Content can be the same but filename different (copy of a file)
  - Hash catches both cases correctly

Hash store is a simple JSON file on disk: {hash: filename}
"""
import json
import hashlib
from pathlib import Path
import config as cfg


def _load_hashes() -> dict:
    p = Path(cfg.HASH_FILE)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def _save_hashes(hashes: dict):
    Path(cfg.HASH_FILE).write_text(json.dumps(hashes, indent=2))


def compute_hash(content: bytes) -> str:
    """Return SHA256 hex digest of file bytes."""
    return hashlib.sha256(content).hexdigest()


def is_duplicate(file_hash: str) -> bool:
    """Return True if this hash has already been ingested."""
    return file_hash in _load_hashes()


def register_hash(file_hash: str, filename: str):
    """Mark a file hash as ingested."""
    hashes = _load_hashes()
    hashes[file_hash] = filename
    _save_hashes(hashes)


def get_all_hashes() -> dict:
    """Return all {hash: filename} pairs."""
    return _load_hashes()


def remove_hash(file_hash: str):
    """Remove a hash (used if ingestion fails mid-way)."""
    hashes = _load_hashes()
    hashes.pop(file_hash, None)
    _save_hashes(hashes)
