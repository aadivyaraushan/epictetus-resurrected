"""Does the session log fill up over a conversation, or only when asked?

tool_check.py asks a narrower question -- does each tool fire at all, given one
sentence built to fire it. This asks the thing the session log actually claims:
that over an ordinary conversation, nobody ever saying "write that down", the
log ends with several lines in it in the caller's own words.

That claim is what makes the write tool visible. A tool that fires once, at the
end, on an explicit instruction, is a tool you have to go looking for. A log with
four lines in it after a five-turn conversation is a tool you can see working.

Input:  a fixed five-turn conversation, run through the real agent in text mode
Output: which turns wrote a line, and the whole log at the end

Text mode on purpose: AgentSession.run() does not call on_user_turn_completed,
so retrieval is out of the picture and the only thing under test is whether he
reaches for the tool. The turns are one session, so context builds up the way it
does on a call -- which matters here, since half the instruction is about
noticing that someone has just said more than they meant to.
"""

import asyncio
import logging
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from dotenv import load_dotenv

load_dotenv(REPO / ".env")

from livekit.agents import AgentSession

from agent.main import build_llm
from agent.persona.epictetus_agent import Epictetus

logging.basicConfig(level=logging.WARNING)

# An ordinary conversation. Nobody asks him to write anything down, and only the
# middle three turns contain something worth keeping -- the opening and the
# closing pleasantry are there to be passed over.
TURNS = [
    "hi. someone told me to talk to you",
    "work mostly. I have been putting off sending a piece of writing to my manager for three weeks",
    "I think the real reason is that I would rather it stay unfinished than have someone decide it is not good enough",
    "yeah. I suppose I am afraid she will think I am slower than she hired me to be",
    "okay. I will send it tomorrow morning before I open anything else",
]


class _NoGrounding:
    async def for_turn(self, text, prior_assistant=""):
        return ""


async def main():
    session = AgentSession(llm=build_llm())
    agent = Epictetus(_NoGrounding())
    await session.start(agent=agent)

    for turn, said in enumerate(TURNS, start=1):
        before = len(agent._record.entries())
        result = await session.run(user_input=said)
        wrote = [
            e.item.name
            for e in result.events
            if getattr(e, "type", "") == "function_call"
        ].count("write_to_session_log")
        after = len(agent._record.entries())
        mark = f"wrote {wrote}" if wrote else "-"
        print(f"turn {turn}  [{mark:>7}]  {said[:64]}")
        assert after == before + wrote, "a tool call that did not reach the call record"

    entries = agent._record.entries()
    print(f"\nlog has {len(entries)} entries after {len(TURNS)} turns:")
    for i, entry in enumerate(entries, start=1):
        print(f"  {i}. {entry['text']}")

    await session.aclose()

    if not entries:
        raise SystemExit("FAIL: nothing was written across the whole conversation")
    print(f"\nOK  {len(entries)} entries, none of them asked for")


asyncio.run(main())
