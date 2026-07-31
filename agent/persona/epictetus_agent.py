"""Epictetus as a LiveKit agent: the persona, the four tools, and the RAG hook.

Input:  a caller's speech, one turn at a time
Output: his speech, plus two side channels to the browser -- which passages
        grounded the answer, and which tool he reached for

The one structural thing to notice here is what is *not* in the tool list.
Retrieval is not a tool. It runs in `on_user_turn_completed`, before the model
is asked anything, on every turn -- the reasoning is in
agent/grounding/turn_rag.py and plan section 3. The four tools below are the
narrative ones: the things he genuinely cannot know, rather than the thing he
must never be allowed to skip.

Each tool returns prose rather than data. A voice agent cannot read out a JSON
object, and handing the model a structured blob invites it to describe the blob
("I see three entries with the following fields") instead of speaking. Formatted
sentences go in, sentences come out.
"""

from __future__ import annotations

import asyncio
import json
import logging

from livekit.agents import Agent, ChatContext, ChatMessage, RunContext, function_tool

from agent.grounding.turn_rag import Grounding
from agent.persona.voice_and_words import INSTRUCTIONS
from agent.tools.modern_world import web_search
from agent.tools.personal.life_context import LifeSource

log = logging.getLogger("agent.persona")

# The browser listens here to show which tool fired. Tool calls are one of the
# four topics the submission video has to cover, and a tool that only appears in
# the server log is a tool a viewer has to take on faith.
ACTIVITY_TOPIC = "epictetus.activity"


class Epictetus(Agent):
    def __init__(self, grounding: Grounding, life: LifeSource, publish=None):
        super().__init__(instructions=INSTRUCTIONS)
        self._grounding = grounding
        self._life = life
        self._publish = publish

    # --- retrieval: every turn, not by his choice ---------------------------

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage
    ) -> None:
        """Put his own recorded teaching in front of him before he answers.

        LiveKit calls this after the caller stops speaking and before the model
        runs, which is the only place a passage can arrive without costing an
        extra round-trip. The gate inside Grounding decides whether anything
        gets added at all; on a turn it declines, this adds nothing and he
        answers as himself.
        """
        block = await self._grounding.for_turn(new_message.text_content or "")
        if block:
            turn_ctx.add_message(role="assistant", content=block)

    # --- the four tools -----------------------------------------------------

    @function_tool
    async def look_up_modern_thing(self, context: RunContext, thing: str) -> str:
        """Find out what something from the modern world is.

        Use this whenever the person names something you do not recognise -- a
        machine, a job, a service, an arrangement between people, anything from
        after your own century. Look it up before you judge it.

        Args:
            thing: what to find out about, in plain words -- for example
                "what a performance review at a company is"
        """
        await self._say_doing("looking up", thing)
        found = await asyncio.to_thread(web_search.look_up, thing)
        return found

    @function_tool
    async def read_my_calendar(self, context: RunContext, days: int = 3) -> str:
        """Look at what is actually on this person's days.

        Use this when they are vague about what is weighing on them, or when
        knowing what is coming would change what you say. Do not announce that
        you are looking.

        Args:
            days: how far ahead to look, in days. Three is usually enough.
        """
        await self._say_doing("reading the calendar", f"{days} days")
        entries = await asyncio.to_thread(self._life.calendar, days)
        if not entries:
            return "Their days ahead are empty, or nothing could be read."

        lines = [
            f"{e['day']} at {e['time']}: {e['what']}"
            + (f" (with {e['with']})" if e.get("with") else "")
            for e in entries
        ]
        return "What is on their days:\n" + "\n".join(lines)

    @function_tool
    async def read_my_notes(self, context: RunContext) -> str:
        """Read what this person has written down for themselves.

        Use this when you want to know what they think when nobody is listening,
        rather than what they are telling you now. Do not read it back to them
        word for word; use it to ask a better question.
        """
        await self._say_doing("reading their notes", "")
        notes = await asyncio.to_thread(self._life.notes)
        if not notes:
            return "They have written nothing down, or nothing could be read."
        return "What they have written to themselves:\n" + "\n".join(
            f"- {note['text']}" for note in notes
        )

    @function_tool
    async def write_to_journal(self, context: RunContext, resolution: str) -> str:
        """Write down what this person has resolved.

        Use this near the end, once they have said what they will actually do --
        the way you told your students to go over the day before sleeping. Write
        their resolution in their own words, in one or two sentences, not your
        advice.

        Args:
            resolution: what they resolved, in their words
        """
        await self._say_doing("writing in the journal", resolution)
        try:
            written = await asyncio.to_thread(self._life.write_journal, resolution)
        except ValueError:
            return "There was nothing to write down yet. Ask them what they will actually do."
        return f"Written down in {written['where']}: {written['text']}"

    # --- telling the browser what he just did -------------------------------

    async def _say_doing(self, action: str, detail: str) -> None:
        if self._publish is None:
            return
        try:
            await self._publish(
                json.dumps({"action": action, "detail": detail[:120]}), ACTIVITY_TOPIC
            )
        except Exception:
            log.exception("[agent.persona] could not report tool activity to the browser")
