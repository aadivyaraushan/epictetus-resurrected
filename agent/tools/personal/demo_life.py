"""The week everyone who is not me gets.

This is what makes the personal tools demonstrable to a stranger. A grader
clicking the public link has no calendar and no notes that this worker can read,
so without a seeded week the three personal tools would be dead weight in the
one call that gets graded.

Input:  nothing -- it is fixed
Output: a calendar, some notes, and a journal that can be written to

It is deliberately a *hard* week rather than a pleasant one, because Epictetus
has nothing to say about an easy Tuesday. A performance review the caller is
dreading, a favour asked by someone who never returns them, a parent's illness,
a job offer that flatters -- every one of those is something the Discourses
actually addresses, so the retrieval has real work to do when he asks about it.

Dates are computed from today so "tomorrow" means tomorrow, but the contents
never change: the same week appears in the video and on the deployed link, which
is what makes a seeded demo read as designed rather than broken.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

log = logging.getLogger("agent.tools.personal")

# (day offset, time, what, who else)
WEEK = [
    (0, "09:30", "Standup", "the team"),
    (0, "14:00", "1:1 with Marcus", "Marcus, my manager"),
    (0, "19:00", "Call Mum about her test results", "Mum"),
    (1, "08:00", "Gym — third week of saying I will", ""),
    (1, "11:00", "Performance review", "Marcus and someone from HR"),
    (1, "16:30", "Coffee with Sophia — she wants a favour again", "Sophia"),
    (2, "10:00", "Deadline: the migration doc nobody has read", ""),
    (2, "13:00", "Lunch with the recruiter from Halcyon", "a recruiter"),
    (2, "18:00", "Dinner with Dad — first time since the argument", "Dad"),
    (3, "09:00", "All-hands: reorg announcement", "everyone"),
    (3, "15:00", "Dentist", ""),
    (4, "12:00", "Nothing scheduled", ""),
]

NOTES = [
    "I keep rehearsing the review in my head at 3am and winning every version of it.",
    "Sophia has asked for four favours this year and returned none. I said yes again.",
    "The Halcyon offer is more money and I think I only want it so I can turn it down.",
    "Mum's results come back Thursday. I have not told anyone I am worried.",
    "I am angry that the migration doc went unread and I have not said so to anyone who could fix it.",
]

SEED_JOURNAL = [
    "Lost my temper in standup over a two-line comment. Nobody else noticed. I did.",
    "Said yes to Sophia before I had finished hearing the question.",
]


def _label(offset: int) -> str:
    if offset == 0:
        return "today"
    if offset == 1:
        return "tomorrow"
    return (date.today() + timedelta(days=offset)).strftime("%A")


class DemoLife:
    def __init__(self) -> None:
        self._journal = list(SEED_JOURNAL)

    def calendar(self, days: int) -> list[dict]:
        today = date.today()
        entries = [
            {
                "day": _label(offset),
                "date": (today + timedelta(days=offset)).isoformat(),
                "time": time,
                "what": what,
                "with": who,
            }
            for offset, time, what, who in WEEK
            if offset < max(1, days)
        ]
        log.info("[agent.tools.personal] demo calendar: %d entries over %d days", len(entries), days)
        return entries

    def notes(self) -> list[dict]:
        return [{"text": text} for text in NOTES]

    def journal(self) -> list[dict]:
        return [{"text": text} for text in self._journal]

    def write_journal(self, text: str) -> dict:
        """Kept in memory for the length of the call.

        It does not survive a restart, and it does not need to -- what it has to
        do is be readable back within the same conversation, so that when
        Epictetus says he has written something down and the caller asks him to
        read it back, something is actually there.
        """
        text = (text or "").strip()
        if not text:
            raise ValueError("refusing to write an empty journal entry")
        self._journal.append(text)
        log.info("[agent.tools.personal] demo journal entry written (%d chars)", len(text))
        return {"written": True, "where": "the demo journal", "text": text}
