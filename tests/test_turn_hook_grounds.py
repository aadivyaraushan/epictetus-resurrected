"""The retrieval hook has to fire the way LiveKit actually calls it.

This is the seam the whole RAG deliverable hangs on, and it is easy to get
wrong in a way nothing else catches: the agent still talks, the tools still
work, the tests still pass, and every answer is simply ungrounded.

Why this test exists in this shape. AgentSession.run(), the obvious way to
drive an agent in a test, never reaches this hook -- it calls generate_reply(),
and on_user_turn_completed is only invoked from the end-of-turn path that STT
and turn detection feed. Its `input_modality="audio"` argument does not change
that; it is recorded as metadata and does not run speech recognition. So a test
built on session.run() would report a grounded agent whether or not grounding
worked at all.

Instead this calls the hook the way the framework does, with the same two
arguments LiveKit passes at agent_activity.py:2362 -- a mutable copy of the
chat context, and the user's message -- and checks that a passage actually
lands in that context.
"""

from __future__ import annotations

import pytest
from livekit.agents import ChatContext, ChatMessage

from agent.persona.epictetus_agent import Epictetus


class _FakeGrounding:
    """Stands in for retrieval so this test is about wiring, not about search."""

    def __init__(self, block: str) -> None:
        self._block = block
        self.asked: list[str] = []

    async def for_turn(self, text: str) -> str:
        self.asked.append(text)
        return self._block


class _FakeLife:
    name = "demo"

    def search_notes(self, query):
        return []


def _agent(block: str) -> tuple[Epictetus, _FakeGrounding]:
    grounding = _FakeGrounding(block)
    return Epictetus(grounding, _FakeLife()), grounding


@pytest.mark.asyncio
async def test_passage_reaches_the_model_on_a_grounded_turn():
    agent, grounding = _agent("PASSAGE: some things are up to us.")
    ctx = ChatContext.empty()

    await agent.on_user_turn_completed(
        ctx, ChatMessage(role="user", content=["I cannot stop worrying about my job"])
    )

    assert grounding.asked == ["I cannot stop worrying about my job"]
    added = " ".join(str(item.content) for item in ctx.items)
    assert "some things are up to us" in added


@pytest.mark.asyncio
async def test_nothing_is_added_when_the_gate_declines():
    """An ungrounded turn must leave the context untouched, not add an empty
    message -- a blank assistant turn is a confusing thing to hand a model."""
    agent, _ = _agent("")
    ctx = ChatContext.empty()

    await agent.on_user_turn_completed(ctx, ChatMessage(role="user", content=["hello"]))

    assert list(ctx.items) == []


@pytest.mark.asyncio
async def test_an_empty_turn_does_not_crash_the_call():
    """new_message.text_content is None when there is no transcript. Raising
    here would kill the turn, and LiveKit swallows the exception -- so the call
    would carry on silently ungrounded."""
    agent, grounding = _agent("PASSAGE: anything")
    ctx = ChatContext.empty()

    await agent.on_user_turn_completed(ctx, ChatMessage(role="user", content=[]))

    assert grounding.asked == [""]


def test_the_hook_matches_the_signature_livekit_calls():
    """LiveKit calls this positionally with the context and by keyword with
    new_message. A rename would silently stop the hook from ever running."""
    import inspect

    from livekit.agents import Agent

    ours = inspect.signature(Epictetus.on_user_turn_completed)
    theirs = inspect.signature(Agent.on_user_turn_completed)
    assert list(ours.parameters) == list(theirs.parameters)
