"""Do the three tools actually fire, and what does a caller have to say to fire them?

The 13-turn live call fired none of them. That is not a bug -- it was a
conversation about the caller's research, and none of the three came up -- but
the brief grades tool calls and the video has to show one, so we need to know
which sentences reliably trigger which tool.

Text mode, real APIs, real model. AgentSession.run() does not invoke
on_user_turn_completed, so there is no retrieval here -- tools only, which is
exactly what is being measured.
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, "/Users/aadivyar/Documents/Internships/Bluejay Take Home")

from dotenv import load_dotenv

load_dotenv("/Users/aadivyar/Documents/Internships/Bluejay Take Home/.env")

from livekit.agents import AgentSession

from agent.main import build_llm
from agent.persona.epictetus_agent import Epictetus
from agent.tools.personal.demo_life import DemoLife
from agent.tools.personal.life_context import LifeSource

logging.basicConfig(level=logging.WARNING)

PROMPTS = [
    ("look_up_modern_thing", "my therapist keeps telling me to try something called cold plunging, what even is that"),
    ("search_my_notion", "what did I write in my notes about work? can you look?"),
    ("write_to_journal", "okay. I resolve to finish the draft by Friday and stop rewriting the intro. write that down for me"),
]


class _NoGrounding:
    async def for_turn(self, text):
        return ""


async def main():
    life = LifeSource(DemoLife(), DemoLife(), name="demo")

    for expected, said in PROMPTS:
        session = AgentSession(llm=build_llm())
        agent = Epictetus(_NoGrounding(), life)
        await session.start(agent=agent)
        try:
            result = await session.run(user_input=said)
        except Exception as e:
            print(f"[{expected}] RUN FAILED: {type(e).__name__}: {str(e)[:200]}")
            continue

        fired = [
            e.item.name
            for e in result.events
            if getattr(e, "type", "") == "function_call"
        ]
        spoken = " ".join(
            e.item.text_content or ""
            for e in result.events
            if getattr(e, "type", "") == "message" and getattr(e.item, "role", "") == "assistant"
        )
        ok = "OK " if expected in fired else "MISS"
        print(f"\n{ok} expected {expected!r}, fired {fired}")
        print(f"     said:  {said[:70]}")
        print(f"     reply: {spoken[:220]}")
        await session.aclose()


asyncio.run(main())
