"""The agent's decisions, tested without a microphone.

Two things in the worker make a decision that can be wrong in a way nobody
would notice on a call:

  1. Whether a turn gets grounded in the Discourses. Getting this wrong means
     Epictetus recites philosophy at "hello" (plan sections 3 and 5).
  2. Which in-call tools exist and how commitments are tagged for the review.

None of those need audio, an LLM, or a LiveKit room, so none of them wait for
a call to be tested.
"""

from __future__ import annotations

import json

import pytest

from agent.grounding.turn_rag import Grounding, worth_searching
from agent.retrieval.search.passage_search import (
    MIN_COSINE_TO_GROUND,
    Passage,
    Retrieval,
)
from agent.session.record import SessionRecord


class FakeSearch:
    """Stands in for PassageSearch. Records what it was asked."""

    def __init__(self, retrieval: Retrieval):
        self.retrieval = retrieval
        self.asked: list[str] = []

    def search(self, question: str) -> Retrieval:
        self.asked.append(question)
        return self.retrieval


class FakeTurnFilter:
    def __init__(self, decision: bool = True, error: Exception | None = None):
        self.decision = decision
        self.error = error
        self.asked: list[tuple[str, str]] = []

    async def should_retrieve(self, prior_assistant: str, current_user: str) -> bool:
        self.asked.append((prior_assistant, current_user))
        if self.error is not None:
            raise self.error
        return self.decision


def grounded_result() -> Retrieval:
    passage = Passage(
        text="Of things some are in our power, and others are not.",
        citation="Book 1, Chapter 1",
        book=1,
        chapter=1,
        title="Of the things which are in our power",
        page=3,
        cosine=0.51,
        fused_score=0.03,
    )
    return Retrieval(passages=[passage], best_cosine=0.51, grounded=True, reason="above gate")


def ambiguous_result(score: float = 0.2451) -> Retrieval:
    result = grounded_result()
    return Retrieval(
        passages=result.passages,
        best_cosine=score,
        grounded=True,
        reason="inside Luna range",
    )


def ungrounded_result() -> Retrieval:
    return Retrieval(passages=[], best_cosine=0.11, grounded=False, reason="below gate")


# --- 1. whether a turn gets grounded ----------------------------------------


def test_the_new_cosine_floor_is_the_highest_value_that_keeps_turn_three():
    assert MIN_COSINE_TO_GROUND == 0.2315


@pytest.mark.parametrize(
    "turn",
    ["yeah", "okay thanks", "cool", "um", "hold on", "", "   "],
)
def test_short_turns_never_reach_the_index(turn):
    """No embedding call for a turn that plainly carries no question.

    This is a latency decision as much as a personality one: retrieval sits
    inside the response loop now, so a turn that cannot possibly need it should
    not pay for it.
    """
    assert worth_searching(turn) is False


@pytest.mark.parametrize(
    "turn",
    [
        "what did you mean about things in our power",
        "how should I deal with a boss who humiliates me",
        "tell me about Agrippinus",
    ],
)
def test_real_questions_do_reach_the_index(turn):
    assert worth_searching(turn) is True


@pytest.mark.asyncio
async def test_a_grounded_turn_puts_passages_in_the_prompt():
    search = FakeSearch(grounded_result())
    grounding = Grounding(search)

    block = await grounding.for_turn("what is in our power")

    assert search.asked == ["what is in our power"]
    assert "Of things some are in our power" in block


@pytest.mark.asyncio
async def test_an_ungrounded_turn_adds_nothing_to_the_prompt():
    """Below the gate, the model is handed no passages at all."""
    grounding = Grounding(FakeSearch(ungrounded_result()))
    assert await grounding.for_turn("hey, can you hear me?") == ""


@pytest.mark.asyncio
async def test_luna_rejects_an_acknowledgment_inside_the_new_score_range():
    published: list[dict] = []

    async def publish(payload: str, topic: str) -> None:
        published.append(json.loads(payload))

    turn_filter = FakeTurnFilter(decision=False)
    grounding = Grounding(
        FakeSearch(ambiguous_result()),
        publish=publish,
        turn_filter=turn_filter,
    )

    block = await grounding.for_turn(
        "That helps. Okay. All right. Thanks.",
        prior_assistant="Does the waiting feel less heavy now?",
    )

    assert block == ""
    assert turn_filter.asked == [
        ("Does the waiting feel less heavy now?", "That helps. Okay. All right. Thanks.")
    ]
    assert published == [
        {
            "sources": [],
            "rag": {
                "status": "rejected",
                "method": "vector + BM25, merged by reciprocal rank fusion",
                "bestCosine": 0.2451,
                "minimumCosine": 0.2315,
                "automaticCosine": 0.36,
                "decision": "Luna rejected",
                "reason": "inside Luna range",
                "selected": 0,
            },
        }
    ]


@pytest.mark.asyncio
async def test_exact_lower_boundary_is_checked_by_luna():
    turn_filter = FakeTurnFilter(decision=True)
    grounding = Grounding(
        FakeSearch(ambiguous_result(score=0.2315)),
        turn_filter=turn_filter,
    )

    block = await grounding.for_turn(
        "I think I will walk away.",
        prior_assistant="Which choice is actually yours?",
    )

    assert "Of things some are in our power" in block
    assert len(turn_filter.asked) == 1


@pytest.mark.asyncio
async def test_score_at_old_gate_bypasses_luna():
    turn_filter = FakeTurnFilter(error=AssertionError("Luna should not be called"))
    grounding = Grounding(
        FakeSearch(ambiguous_result(score=0.36)),
        turn_filter=turn_filter,
    )

    block = await grounding.for_turn("How should I handle this decision?")

    assert "Of things some are in our power" in block
    assert turn_filter.asked == []


@pytest.mark.asyncio
async def test_score_below_new_floor_bypasses_luna():
    turn_filter = FakeTurnFilter(error=AssertionError("Luna should not be called"))
    grounding = Grounding(FakeSearch(ungrounded_result()), turn_filter=turn_filter)

    assert await grounding.for_turn("hey can you hear me now") == ""
    assert turn_filter.asked == []


@pytest.mark.asyncio
async def test_production_luna_failure_is_logged_and_keeps_the_panel_empty(caplog):
    published: list[dict] = []

    async def publish(payload: str, topic: str) -> None:
        published.append(json.loads(payload))

    turn_filter = FakeTurnFilter(error=TimeoutError("Luna timed out"))
    grounding = Grounding(
        FakeSearch(ambiguous_result()),
        publish=publish,
        turn_filter=turn_filter,
        hide_filter_errors=True,
    )

    with caplog.at_level("ERROR"):
        block = await grounding.for_turn("I think I will walk away")

    assert block == ""
    assert published == [
        {
            "sources": [],
            "rag": {
                "status": "error",
                "method": "vector + BM25, merged by reciprocal rank fusion",
                "bestCosine": 0.2451,
                "minimumCosine": 0.2315,
                "automaticCosine": 0.36,
                "decision": "Luna error",
                "reason": "Luna timed out or failed; answered without passages",
                "selected": 0,
            },
        }
    ]
    assert "Luna filter failed" in caplog.text
    assert "showing no sources" in caplog.text


@pytest.mark.asyncio
async def test_development_luna_failure_stops_the_request():
    turn_filter = FakeTurnFilter(error=TimeoutError("Luna timed out"))
    grounding = Grounding(
        FakeSearch(ambiguous_result()),
        turn_filter=turn_filter,
        hide_filter_errors=False,
    )

    with pytest.raises(TimeoutError, match="Luna timed out"):
        await grounding.for_turn("I think I will walk away")


@pytest.mark.asyncio
async def test_the_prompt_block_never_names_a_book_or_chapter():
    """Epictetus speaks; the panel cites. Handing the model chapter numbers is
    handing it something to read aloud (plan section 3)."""
    grounding = Grounding(FakeSearch(grounded_result()))
    block = await grounding.for_turn("what is in our power")
    assert "Book 1" not in block
    assert "Chapter" not in block


@pytest.mark.asyncio
async def test_the_source_panel_is_told_what_was_used():
    published: list[tuple[str, str]] = []

    async def publish(payload: str, topic: str) -> None:
        published.append((payload, topic))

    grounding = Grounding(FakeSearch(grounded_result()), publish=publish)
    await grounding.for_turn("what is in our power")

    assert len(published) == 1
    payload, topic = published[0]
    body = json.loads(payload)
    assert topic == Grounding.PANEL_TOPIC
    assert body["sources"][0]["citation"] == "Book 1, Chapter 1"
    assert body["sources"][0]["text"].startswith("Of things some are")
    assert body["rag"] == {
        "status": "grounded",
        "method": "vector + BM25, merged by reciprocal rank fusion",
        "bestCosine": 0.51,
        "minimumCosine": 0.2315,
        "automaticCosine": 0.36,
        "decision": "accepted automatically",
        "reason": "above gate",
        "selected": 1,
    }


@pytest.mark.asyncio
async def test_the_panel_is_cleared_when_a_turn_is_not_grounded():
    """Otherwise the panel keeps showing the last answer's chapter while
    Epictetus talks about something else entirely -- a citation for a claim he
    did not make."""
    published: list[dict] = []

    async def publish(payload: str, topic: str) -> None:
        published.append(json.loads(payload))

    grounding = Grounding(FakeSearch(ungrounded_result()), publish=publish)
    await grounding.for_turn("what's on my calendar tomorrow?")

    assert published == [
        {
            "sources": [],
            "rag": {
                "status": "rejected",
                "method": "vector + BM25, merged by reciprocal rank fusion",
                "bestCosine": 0.11,
                "minimumCosine": 0.2315,
                "automaticCosine": 0.36,
                "decision": "below minimum cosine",
                "reason": "below gate",
                "selected": 0,
            },
        }
    ]


@pytest.mark.asyncio
async def test_a_short_turn_publishes_a_visible_skip_decision():
    published: list[dict] = []

    async def publish(payload: str, topic: str) -> None:
        published.append(json.loads(payload))

    grounding = Grounding(FakeSearch(grounded_result()), publish=publish)
    await grounding.for_turn("okay thanks")

    assert published == [
        {
            "sources": [],
            "rag": {
                "status": "skipped",
                "method": "word-count check before retrieval",
                "bestCosine": None,
                "minimumCosine": 0.2315,
                "automaticCosine": 0.36,
                "decision": "turn too short",
                "reason": "fewer than 4 words",
                "selected": 0,
            },
        }
    ]


@pytest.mark.asyncio
async def test_a_failing_index_does_not_end_the_call():
    """If retrieval throws, he answers ungrounded rather than going silent."""

    class BrokenSearch:
        def search(self, question: str) -> Retrieval:
            raise RuntimeError("index unreadable")

    published: list[dict] = []

    async def publish(payload: str, topic: str) -> None:
        published.append(json.loads(payload))

    grounding = Grounding(BrokenSearch(), publish=publish)
    assert await grounding.for_turn("what is in our power") == ""
    assert published == [
        {
            "sources": [],
            "rag": {
                "status": "error",
                "method": "vector + BM25, merged by reciprocal rank fusion",
                "bestCosine": None,
                "minimumCosine": 0.2315,
                "automaticCosine": 0.36,
                "decision": "retrieval error",
                "reason": "retrieval failed; answered without passages",
                "selected": 0,
            },
        }
    ]


# --- 2. which tools exist at all ---------------------------------------------


EXPECTED_TOOLS = {"look_up_modern_thing", "write_to_session_log"}


def test_the_agent_exposes_exactly_the_two_call_tools():
    """Plan section 4. A tool that is registered but half-removed still shows up
    in the LLM's tool list, so it can still be called mid-call and fail."""
    from agent.persona.epictetus_agent import Epictetus

    registered = {
        name
        for name in dir(Epictetus)
        if getattr(getattr(Epictetus, name, None), "__livekit_tool_info", None) is not None
    }
    assert registered == EXPECTED_TOOLS


def test_the_agent_cannot_search_private_notion_pages():
    from agent.persona.epictetus_agent import Epictetus

    assert not hasattr(Epictetus, "search_my_notion")


def test_a_session_record_keeps_reflections_and_commitments_in_order():
    record = SessionRecord()
    record.write("reflection", "The fear is mostly about status.")
    record.write("commitment", "Send the outline tomorrow morning.")

    assert record.entries() == [
        {"entry": 1, "kind": "reflection", "text": "The fear is mostly about status."},
        {"entry": 2, "kind": "commitment", "text": "Send the outline tomorrow morning."},
    ]
    assert record.latest_commitment() == "Send the outline tomorrow morning."


def test_the_session_log_starts_empty():
    assert SessionRecord().entries() == []


def test_a_written_entry_is_numbered_so_he_can_say_it_out_loud():
    """ "That is the third thing I have written down" is checkable by a listener
    in a way that "I have written it down" is not."""
    record = SessionRecord()
    assert record.write("reflection", "first")["entry"] == 1
    assert record.write("commitment", "second")["entry"] == 2


def test_an_empty_entry_is_refused_rather_than_written():
    """A blank line in the log would look like a write that worked."""
    with pytest.raises(ValueError):
        SessionRecord().write("reflection", "   ")


def test_a_session_entry_kind_must_be_known():
    with pytest.raises(ValueError):
        SessionRecord().write("guess", "Something")


@pytest.mark.asyncio
async def test_commitment_activity_is_tagged_for_the_browser_review():
    from agent.persona.epictetus_agent import Epictetus

    published = []

    async def publish(payload, topic):
        published.append((json.loads(payload), topic))

    commitment = "Send the revised outline tomorrow morning, then message Dana with the three decisions and ask her to confirm the Friday review time."
    agent = Epictetus(FakeSearch(ungrounded_result()), publish=publish)
    await agent._say_doing("writing in the session log", commitment, "commitment")

    assert published == [
        (
            {
                "action": "writing in the session log",
                "detail": commitment[:120],
                "kind": "commitment",
                "commitment": commitment,
            },
            "epictetus.activity",
        )
    ]
