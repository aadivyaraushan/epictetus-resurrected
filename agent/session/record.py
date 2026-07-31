"""A small in-memory record for one call.

The browser receives each entry as tool activity and builds the review from the
call transcript. Nothing here reaches Notion; only the completed review route
can do that after the caller has edited and approved it.
"""

from __future__ import annotations

from typing import Literal

EntryKind = Literal["reflection", "commitment"]


class SessionRecord:
    def __init__(self) -> None:
        self._entries: list[dict] = []

    def write(self, kind: EntryKind, text: str) -> dict:
        clean = text.strip()
        if kind not in ("reflection", "commitment"):
            raise ValueError("unknown session entry kind")
        if not clean:
            raise ValueError("empty session entry")
        entry = {"entry": len(self._entries) + 1, "kind": kind, "text": clean}
        self._entries.append(entry)
        return dict(entry)

    def entries(self) -> list[dict]:
        return [dict(entry) for entry in self._entries]

    def latest_commitment(self) -> str:
        for entry in reversed(self._entries):
            if entry["kind"] == "commitment":
                return entry["text"]
        return ""
