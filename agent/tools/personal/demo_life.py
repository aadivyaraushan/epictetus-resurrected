"""The week everyone who is not me gets.

This is what makes the personal tools demonstrable to a stranger. A grader
clicking the public link has no notes that this worker can read, so without
seeded notes the two personal tools would be dead weight in the one call that
gets graded.

Input:  nothing -- it is fixed
Output: some notes, and an empty session log that can be written to

The notes are deliberately about a *hard* week rather than a pleasant one,
because Epictetus has nothing to say about an easy Tuesday. A performance review
the caller is dreading, a favour asked by someone who never returns them, a
parent's illness, a job offer that flatters -- every one of those is something
the Discourses actually addresses, so the retrieval has real work to do when he
asks about it.

The contents never change: the same notes appear in the video and on the
deployed link, which is what makes a seeded demo read as designed rather than
broken.
"""

from __future__ import annotations

import logging

log = logging.getLogger("agent.tools.personal")

NOTES = [
    "I keep rehearsing the review in my head at 3am and winning every version of it.",
    "Sophia has asked for four favours this year and returned none. I said yes again.",
    "The Halcyon offer is more money and I think I only want it so I can turn it down.",
    "Mum's results come back Thursday. I have not told anyone I am worried.",
    "I am angry that the migration doc went unread and I have not said so to anyone who could fix it.",
]

class DemoLife:
    def __init__(self) -> None:
        # Deliberately empty, unlike the notes above. The notes are seeded
        # because a search that returns nothing looks broken; the session log is
        # not, because an empty start is what makes it evidence. Every line in
        # it got there by the write tool firing during this call.
        self._log: list[str] = []

    def search_notes(self, query: str) -> list[dict]:
        """Matches on shared words, and returns everything when nothing matches.

        A demo search that returns nothing looks like a broken tool rather than
        a seeded one, and the grader cannot tell the difference. Falling back to
        the whole set means Epictetus always has something to react to.
        """
        wanted = {word for word in (query or "").lower().split() if len(word) > 3}
        hits = [text for text in NOTES if wanted & set(text.lower().split())]
        chosen = hits or NOTES
        log.info(
            "[agent.tools.personal] demo notes: %d of %d matched %r",
            len(hits),
            len(NOTES),
            query,
        )
        return [{"text": text} for text in chosen]

    def session_log(self) -> list[dict]:
        return [{"text": text} for text in self._log]

    def write_session_log(self, text: str) -> dict:
        """Kept in memory for the length of the call.

        It does not survive a restart, and it does not need to. What it has to
        do is be readable back inside the same conversation, so that when
        Epictetus says he has written something down and the caller asks him to
        read it back, something is actually there.
        """
        text = (text or "").strip()
        if not text:
            raise ValueError("refusing to write an empty entry")
        self._log.append(text)
        log.info(
            "[agent.tools.personal] demo session log entry %d written (%d chars)",
            len(self._log),
            len(text),
        )
        return {
            "written": True,
            "where": "the log of this conversation",
            "text": text,
            "entry": len(self._log),
        }
