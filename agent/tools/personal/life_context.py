"""Where Epictetus's questions about your life get answered from.

Plan section 4. Three of the four tools read or write personal data, and the
grader is not me: my calendar and my Notion return nothing useful to them, and
pointing a public link at my real accounts would be handing a company access to
both. So each personal tool sits behind one interface with two implementations
-- live (my accounts) and a seeded demo week that everyone else gets. The agent
cannot tell which it is talking to.

Input:  the caller's participant record from LiveKit, and whether live
        credentials are configured at all
Output: one LifeContext, plus a name for it that goes in the logs

How the switch works, and why it is a secret rather than a name. The first idea
was to check the caller's display name against mine. That is not safe: this
design is described in a public README and a public video, and the link stays
live for two weeks, so anyone who read either could type my name in and read my
real calendar. A guessable string is not a credential.

Instead the caller types a passphrase on the start screen. The token endpoint
compares it against an environment variable and writes the verdict into the
access token it mints, which is signed with the LiveKit API secret. The caller
carries that token but cannot alter it, so they cannot promote themselves. This
worker only reads the verdict.

Demo is the default and the fallback. No passphrase, a wrong one, a missing
credential, or an API call that fails all land on demo -- so an expired OAuth
grant degrades to a working demo instead of a dead tool in the middle of a call.
The grader never sees an error; they see Epictetus reading a plausible week.
"""

from __future__ import annotations

import json
import logging
from typing import Protocol

log = logging.getLogger("agent.tools.personal")


class LifeContext(Protocol):
    """What Epictetus can find out about the caller's life, and write back."""

    def calendar(self, days: int) -> list[dict]: ...

    def notes(self) -> list[dict]: ...

    def journal(self) -> list[dict]: ...

    def write_journal(self, text: str) -> dict: ...


def choose_life_backend(participant, live_available: bool) -> str:
    """"live" or "demo" -- the name of the backend this caller has earned.

    `participant` is the LiveKit remote participant; only its signed metadata is
    consulted. Anything unparseable, absent, or unsupported by configured
    credentials means demo.
    """
    raw = getattr(participant, "metadata", "") or ""
    try:
        claims = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        if raw:
            log.warning("[agent.tools.personal] unreadable participant metadata; using demo")
        return "demo"

    if not isinstance(claims, dict) or claims.get("life_backend") != "live":
        return "demo"

    if not live_available:
        log.warning(
            "[agent.tools.personal] token asked for the live backend but no live "
            "credentials are configured; using demo"
        )
        return "demo"

    log.info("[agent.tools.personal] caller unlocked the live backend")
    return "live"


class LifeSource:
    """A LifeContext that falls back to the demo week when the live one fails.

    Every call is wrapped, not just the first, because credentials expire in the
    middle of things. A tool that raises mid-call is a worse outcome than a tool
    that quietly answers from the demo week: one ends the illusion, the other
    keeps the conversation going.
    """

    def __init__(self, primary: LifeContext, fallback: LifeContext, name: str):
        self._primary = primary
        self._fallback = fallback
        self.name = name

    def _try(self, method: str, *args):
        try:
            return getattr(self._primary, method)(*args)
        except Exception:
            log.exception(
                "[agent.tools.personal] live %s failed; falling back to the demo week", method
            )
            return getattr(self._fallback, method)(*args)

    def calendar(self, days: int) -> list[dict]:
        return self._try("calendar", days)

    def notes(self) -> list[dict]:
        return self._try("notes")

    def journal(self) -> list[dict]:
        return self._try("journal")

    def write_journal(self, text: str) -> dict:
        return self._try("write_journal", text)


def build_life_context(participant, *, live_factory=None) -> LifeSource:
    """Pick the backend for one caller and wrap it with the demo fallback."""
    from agent.tools.personal.demo_life import DemoLife
    from agent.tools.personal.live_life import LiveLife, live_credentials_present

    demo = DemoLife()
    live_factory = live_factory or LiveLife
    choice = choose_life_backend(participant, live_available=live_credentials_present())

    if choice == "demo":
        return LifeSource(primary=demo, fallback=demo, name="demo")
    return LifeSource(primary=live_factory(), fallback=demo, name="live")
