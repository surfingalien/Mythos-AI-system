"""Persistent long-term memory: a small JSON store of remembered facts.

Facts are injected into the LLM system prompt each session and can be
added/searched/removed via the memory tools.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path


class Memory:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._facts: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self._facts = data.get("facts", [])
            except (json.JSONDecodeError, OSError):
                self._facts = []

    def _save(self) -> None:
        self.path.write_text(
            json.dumps({"facts": self._facts}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def remember(self, fact: str) -> None:
        fact = fact.strip()
        if not fact:
            return
        if any(f["text"].lower() == fact.lower() for f in self._facts):
            return
        self._facts.append({
            "text": fact,
            "created": datetime.datetime.now().isoformat(timespec="seconds"),
        })
        self._save()

    def forget(self, needle: str) -> int:
        """Remove facts containing `needle` (case-insensitive). Returns count removed."""
        needle = needle.lower().strip()
        before = len(self._facts)
        self._facts = [f for f in self._facts if needle not in f["text"].lower()]
        if len(self._facts) != before:
            self._save()
        return before - len(self._facts)

    def search(self, query: str) -> list[str]:
        words = set(query.lower().split())
        scored = []
        for f in self._facts:
            hits = sum(f["text"].lower().count(w) for w in words)
            if hits:
                scored.append((hits, f["text"]))
        scored.sort(reverse=True)
        return [text for _, text in scored]

    def all_facts(self) -> list[str]:
        return [f["text"] for f in self._facts]
