"""Epictetus as a LiveKit agent: the persona, the two tools, and the RAG hook.

Input:  a caller's speech, one turn at a time
Output: his speech, plus two side channels to the browser -- which passages
        grounded the answer, and which tool he reached for

The one structural thing to notice here is what is *not* in the tool list.
Retrieval is not a tool. It runs in `on_user_turn_completed`, before the model
is asked anything, on every turn -- the reasoning is in
agent/grounding/turn_rag.py and plan section 3. The two tools below are the
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
from agent.session.record import EntryKind, SessionRecord

log = logging.getLogger("agent.persona")

# The browser listens here to show which tool fired. Tool calls are one of the
# four topics the submission video has to cover, and a tool that only appears in
# the server log is a tool a viewer has to take on faith.
ACTIVITY_TOPIC = "epictetus.activity"


class Epictetus(Agent):
    def __init__(self, grounding: Grounding, publish=None):
        super().__init__(instructions=INSTRUCTIONS)
        self._grounding = grounding
        self._record = SessionRecord()
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

    # --- the two tools ------------------------------------------------------

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
    async def write_to_session_log(
        self, context: RunContext, note: str, kind: EntryKind
    ) -> str:
        """Write one line into the record you are keeping of this conversation.

        Keep it as you go, not only at the end. Write a line whenever something
        is worth keeping: when they finally say what is actually wrong, when
        something you said lands, when they name what they will do. Arrian kept
        such a record of your own conversations, which is the only reason any of
        them survive.

        Write what *they* said, in their words, in a sentence or two. Not your
        advice, and not a summary of the whole call.

        Args:
            note: the thing worth keeping, in their words
            kind: "commitment" only when the person clearly says they will do
                an action; otherwise "reflection"
        """
        await self._say_doing("writing in the session log", note, kind)
        try:
            written = self._record.write(kind, note)
        except ValueError:
            return "There was nothing worth writing yet. Keep listening."
        return f"Entry {written['entry']} in this call: {written['text']}"

    # --- telling the browser what he just did -------------------------------

    async def _say_doing(
        self, action: str, detail: str, kind: EntryKind | None = None
    ) -> None:
        if self._publish is None:
            return
        try:
            await self._publish(
                json.dumps(
                    {
                        "action": action,
                        "detail": detail[:120],
                        "kind": kind,
                        "commitment": detail if kind == "commitment" else None,
                    }
                ),
                ACTIVITY_TOPIC,
            )
        except Exception:
            log.exception("[agent.persona] could not report tool activity to the browser")
