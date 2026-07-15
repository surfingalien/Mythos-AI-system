"""Notes tool: lightweight retrieval over a folder of personal text/markdown notes.

Simple keyword scoring — no embedding dependencies — so it works offline.
Point NOTES_DIR at a folder of .txt/.md files.
"""

from __future__ import annotations

import re
from pathlib import Path

from jarvis.config import config
from jarvis.tools.registry import tool

_EXTENSIONS = {".txt", ".md", ".markdown"}


def search_notes_dir(directory: str | Path, query: str, top_k: int = 3) -> list[tuple[str, str]]:
    """Return up to top_k (filename, snippet) pairs ranked by keyword overlap."""
    words = {w for w in re.findall(r"\w+", query.lower()) if len(w) > 2}
    if not words:
        return []
    scored: list[tuple[int, str, str]] = []
    root = Path(directory)
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in _EXTENSIONS or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lower = text.lower()
        score = sum(lower.count(w) for w in words)
        if score == 0:
            continue
        # Snippet: first paragraph containing any query word
        snippet = ""
        for para in text.split("\n\n"):
            if any(w in para.lower() for w in words):
                snippet = " ".join(para.split())[:300]
                break
        scored.append((score, path.name, snippet or " ".join(text.split())[:300]))
    scored.sort(reverse=True)
    return [(name, snippet) for _, name, snippet in scored[:top_k]]


@tool(
    description="Search the user's personal notes folder and return the most relevant excerpts.",
    parameters={"query": {"type": "string", "description": "What to search the notes for"}},
    enabled=lambda: bool(config.notes_dir),
)
def search_notes(query: str) -> str:
    root = Path(config.notes_dir)
    if not root.is_dir():
        return f"The notes folder {config.notes_dir} doesn't exist."
    results = search_notes_dir(root, query)
    if not results:
        return "I couldn't find anything about that in your notes."
    parts = [f"From {name}: {snippet}" for name, snippet in results]
    return " || ".join(parts)
