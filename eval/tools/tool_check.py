"""Do the two tools actually fire, and what does a caller have to say to fire them?

The 13-turn live call fired none of them. That is not a bug -- it was a
conversation about the caller's research, and neither tool came up -- but
the brief grades tool calls and the video has to show one, so we need to know
which sentences reliably trigger which tool.

Text mode, real APIs, real model. AgentSession.run() does not invoke
on_user_turn_completed, so there is no retrieval here -- tools only, which is
exactly what is being measured.
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

PROMPTS = [
    ("look_up_modern_thing", "my therapist keeps telling me to try something called cold plunging, what even is that"),
    # Deliberately not a resolution and not an instruction to write. The old
    # journal tool only fired on "I resolve to X, write that down"; a session
    # log has to fire on an ordinary admission in the middle of a conversation,
    # unprompted, or it is the same rare tool under a new name.
    ("write_to_session_log", "I think the real reason I have not sent it is that I would rather it stay unfinished than be judged"),
    # The other half of the session-log test. Telling him to keep a record hard
    # enough that it fires unprompted is easy; the failure that costs is a tool
    # call on "can you hear me", which the caller sees in the panel and which
    # makes the log worthless as evidence of anything.
    ("nothing", "hi, can you hear me okay?"),
]


class _NoGrounding:
    async def for_turn(self, text, prior_assistant=""):
        return ""


async def main():
    # `python eval/tools/tool_check.py log` runs only the prompts whose tool name
    # contains "log". Iterating on one tool's wording should cost one model call,
    # not three.
    only = sys.argv[1] if len(sys.argv) > 1 else ""

    for expected, said in PROMPTS:
        if only and only not in expected:
            continue
        session = AgentSession(llm=build_llm())
        agent = Epictetus(_NoGrounding())
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
        if expected == "nothing":
            ok = "OK " if not fired else "FIRED"
        else:
            ok = "OK " if expected in fired else "MISS"
        print(f"\n{ok} expected {expected!r}, fired {fired}")
        print(f"     said:  {said[:70]}")
        print(f"     reply: {spoken[:220]}")
        await session.aclose()


asyncio.run(main())
