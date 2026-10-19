"""Text utility functions."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path


def slugify(text: str, max_length: int = 80) -> str:
    """Convert text to a URL-friendly slug."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text[:max_length]


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length, adding suffix if truncated."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)].rstrip() + suffix


def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def estimate_duration_seconds(word_count: int, wpm: int = 150) -> float:
    """Estimate narration duration in seconds from word count."""
    return (word_count / wpm) * 60


def parse_visual_markers(text: str) -> list[dict]:
    """Extract [VISUAL: ...] markers from script text."""
    pattern = r"\[VISUAL:\s*(.*?)\]"
    markers = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        markers.append({
            "full": match.group(0),
            "description": match.group(1).strip(),
            "position": match.start(),
        })
    return markers


def extract_code_blocks(text: str) -> list[dict]:
    """Extract code blocks from markdown text."""
    pattern = r"```(\w+)?\n(.*?)```"
    blocks = []
    for match in re.finditer(pattern, text, re.DOTALL):
        blocks.append({
            "language": match.group(1) or "text",
            "code": match.group(2).strip(),
            "full": match.group(0),
        })
    return blocks
