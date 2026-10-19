"""File utility functions."""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    """Ensure a directory exists, creating it if needed."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_write_text(path: str | Path, content: str, encoding: str = "utf-8") -> Path:
    """Write text to a file atomically (write to temp, then rename)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(content, encoding=encoding)
    tmp.replace(p)
    return p


def safe_read_text(path: str | Path, encoding: str = "utf-8") -> str:
    """Read text from a file."""
    return Path(path).read_text(encoding=encoding)


def get_file_hash(path: str | Path, algorithm: str = "md5") -> str:
    """Compute a hash of a file's contents."""
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read, b""):
            h.update(chunk)
    return h.hexdigest()


def cleanup_old_files(directory: str | Path, max_age_hours: int = 24) -> int:
    """Delete files older than max_age_hours from a directory."""
    directory = Path(directory)
    if not directory.exists():
        return 0

    cutoff = time.time() - (max_age_hours * 3600)
    removed = 0
    for f in directory.rglob("*"):
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink(missing_ok=True)
            removed += 1
    return removed
