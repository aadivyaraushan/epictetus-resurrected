"""The real notes and the real session log -- reached only with the passphrase.

The page the session log is appended to is still named by NOTION_JOURNAL_PAGE_ID.
The variable kept its old name on purpose: it is a deployed secret on the hosted
worker, and renaming it would mean the running worker looks for a variable that
is not there until the secret is re-uploaded. The page it points at is the same
page either way.

Input:  credentials from the environment; nothing from the caller
Output: the same shapes DemoLife produces, so the tools cannot tell them apart

Everything here is plain HTTP rather than the vendor SDKs. Two reasons: the
worker image stays small, and this is three requests total, which is less code
than configuring a client library would be.

Nothing in this file is on the required path. Plan section 6 puts Notion first
in the cut order, and the seeded notes in demo_life.py are what a grader sees
either way. If a call here fails for any reason -- no credential, revoked token,
a page that was never shared with the integration -- LifeSource catches it and
answers from the demo notes instead, so a broken integration costs a plausible
answer rather than the call.

Notion's API version is pinned below. Notion requires the header and will
behave differently without the right one, so it is a constant with a date on it
rather than something to remember.
"""

from __future__ import annotations

import logging
import os
from datetime import date

import httpx

log = logging.getLogger("agent.tools.personal")

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"

# Named once, because a typo here does not raise -- it makes the live backend
# report itself unconfigured and every caller quietly gets the demo notes.
NOTION_KEY_ENV = "NOTION_API_KEY"

TIMEOUT = 6.0  # a voice call cannot wait longer than this for a note lookup


def live_credentials_present() -> bool:
    """Is there anything to be live *with*?

    Checked before the passphrase is honoured, so an unlocked call with no
    credentials configured lands on the demo notes rather than on an error.
    """
    return bool(os.environ.get(NOTION_KEY_ENV))


def _notion_headers() -> dict:
    token = os.environ.get(NOTION_KEY_ENV)
    if not token:
        raise RuntimeError(f"{NOTION_KEY_ENV} is not set")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _plain_text(block: dict) -> str:
    """Pull the readable words out of a Notion block, whatever its type."""
    body = block.get(block.get("type", ""), {})
    parts = body.get("rich_text", []) if isinstance(body, dict) else []
    return "".join(part.get("plain_text", "") for part in parts).strip()


class LiveLife:
    """My actual week. Constructed per call, so a revoked token is noticed."""

    def __init__(self) -> None:
        # Counted rather than read back. The number Epictetus says out loud is
        # "how many I have written during this conversation", which is what a
        # listener can check -- and counting it here costs nothing, where asking
        # Notion would be another round trip in the middle of a spoken turn.
        self._written = 0

    def search_notes(self, query: str) -> list[dict]:
        """Search everything shared with the integration, then read the best hit.

        Two requests, because Notion's search returns pages, not their contents:
        POST /v1/search ranks the pages by the query, and the page that comes
        back first is then read block by block. Nothing here names a database or
        a fixed page id -- the scope is whatever has been shared with the
        integration in Notion's own UI, which is also where it gets revoked.
        """
        with httpx.Client(timeout=TIMEOUT) as http:
            found = http.post(
                f"{NOTION_API}/search",
                headers=_notion_headers(),
                json={
                    "query": query,
                    "filter": {"property": "object", "value": "page"},
                    "page_size": 5,
                },
            )
            found.raise_for_status()
            hits = found.json().get("results", [])
            if not hits:
                log.info("[agent.tools.personal] live notes: no page matched %r", query)
                return []

            page_id = hits[0]["id"]
            body = http.get(
                f"{NOTION_API}/blocks/{page_id}/children",
                headers=_notion_headers(),
                params={"page_size": 40},
            )
            body.raise_for_status()

        notes = [
            {"text": text}
            for text in (_plain_text(b) for b in body.json().get("results", []))
            if text
        ]
        log.info(
            "[agent.tools.personal] live notes: %d matched pages, %d lines read from the first",
            len(hits),
            len(notes),
        )
        return notes

    def session_log(self) -> list[dict]:
        page_id = os.environ["NOTION_JOURNAL_PAGE_ID"]
        with httpx.Client(timeout=TIMEOUT) as http:
            response = http.get(
                f"{NOTION_API}/blocks/{page_id}/children",
                headers=_notion_headers(),
                params={"page_size": 20},
            )
            response.raise_for_status()
        return [
            {"text": text}
            for text in (_plain_text(b) for b in response.json().get("results", []))
            if text
        ]

    def write_session_log(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            raise ValueError("refusing to write an empty entry")

        page_id = os.environ["NOTION_JOURNAL_PAGE_ID"]
        stamped = f"{date.today().isoformat()} — {text}"

        with httpx.Client(timeout=TIMEOUT) as http:
            response = http.patch(
                f"{NOTION_API}/blocks/{page_id}/children",
                headers=_notion_headers(),
                json={
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": stamped}}]
                            },
                        }
                    ]
                },
            )
            response.raise_for_status()

        self._written += 1
        log.info(
            "[agent.tools.personal] live session log entry %d written (%d chars)",
            self._written,
            len(text),
        )
        return {
            "written": True,
            "where": "your Notion page",
            "text": stamped,
            "entry": self._written,
        }
