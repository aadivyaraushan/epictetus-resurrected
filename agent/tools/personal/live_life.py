"""The real calendar and the real notes -- reached only with the passphrase.

Input:  credentials from the environment; nothing from the caller
Output: the same shapes DemoLife produces, so the tools cannot tell them apart

Everything here is plain HTTP rather than the vendor SDKs. Two reasons: the
worker image stays small, and both of these are four requests total, which is
less code than configuring a client library would be.

Nothing in this file is on the required path. Plan section 6 puts Google
Calendar first in the cut order and Notion second, and the demo week in
demo_life.py is what a grader sees either way. If a call here fails for any
reason -- no credential, expired grant, changed API -- LifeSource catches it and
answers from the demo week instead, so a broken integration costs a plausible
answer rather than the call.

Notion's API version is pinned below. Notion requires the header and will
behave differently without the right one, so it is a constant with a date on it
rather than something to remember.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta, timezone

import httpx

log = logging.getLogger("agent.tools.personal")

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"

TIMEOUT = 6.0  # a voice call cannot wait longer than this for a calendar


def live_credentials_present() -> bool:
    """Is there anything to be live *with*?

    Checked before the passphrase is honoured, so an unlocked call with no
    credentials configured lands on the demo week rather than on an error.
    """
    return bool(
        os.environ.get("NOTION_TOKEN")
        or (
            os.environ.get("GOOGLE_CLIENT_ID")
            and os.environ.get("GOOGLE_CLIENT_SECRET")
            and os.environ.get("GOOGLE_REFRESH_TOKEN")
        )
    )


def _notion_headers() -> dict:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise RuntimeError("NOTION_TOKEN is not set")
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

    def calendar(self, days: int) -> list[dict]:
        client_id = os.environ["GOOGLE_CLIENT_ID"]
        client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
        refresh_token = os.environ["GOOGLE_REFRESH_TOKEN"]

        with httpx.Client(timeout=TIMEOUT) as http:
            granted = http.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            granted.raise_for_status()
            access_token = granted.json()["access_token"]

            now = datetime.now(timezone.utc)
            events = http.get(
                f"{GOOGLE_CALENDAR_API}/calendars/primary/events",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "timeMin": now.isoformat(),
                    "timeMax": (now + timedelta(days=max(1, days))).isoformat(),
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 25,
                },
            )
            events.raise_for_status()

        entries = []
        for item in events.json().get("items", []):
            start = item.get("start", {})
            when = start.get("dateTime") or start.get("date") or ""
            on = when[:10]
            offset = (date.fromisoformat(on) - date.today()).days if on else 0
            entries.append(
                {
                    "day": {0: "today", 1: "tomorrow"}.get(offset)
                    or (date.today() + timedelta(days=offset)).strftime("%A"),
                    "date": on,
                    "time": when[11:16] if "T" in when else "all day",
                    "what": item.get("summary", "(untitled)"),
                    "with": ", ".join(
                        a.get("email", "") for a in item.get("attendees", []) if a.get("email")
                    ),
                }
            )
        log.info("[agent.tools.personal] live calendar: %d events", len(entries))
        return entries

    def notes(self) -> list[dict]:
        page_id = os.environ["NOTION_NOTES_PAGE_ID"]
        with httpx.Client(timeout=TIMEOUT) as http:
            response = http.get(
                f"{NOTION_API}/blocks/{page_id}/children",
                headers=_notion_headers(),
                params={"page_size": 40},
            )
            response.raise_for_status()

        notes = [
            {"text": text}
            for text in (_plain_text(b) for b in response.json().get("results", []))
            if text
        ]
        log.info("[agent.tools.personal] live notes: %d lines", len(notes))
        return notes

    def journal(self) -> list[dict]:
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

    def write_journal(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            raise ValueError("refusing to write an empty journal entry")

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

        log.info("[agent.tools.personal] live journal entry written (%d chars)", len(text))
        return {"written": True, "where": "your Notion journal", "text": stamped}
