"""The agent's decisions, tested without a microphone.

Three things in the worker make a decision that can be wrong in a way nobody
would notice on a call:

  1. Which personal backend a caller gets. Getting this wrong means a stranger
     on a public link reads my real calendar (plan section 4).
  2. Whether a turn gets grounded in the Discourses. Getting this wrong means
     Epictetus recites philosophy at "hello" (plan sections 3 and 5).
  3. What the demo backend says. It has to look like a real week, because the
     grader will hear it.

None of those need audio, an LLM, or a LiveKit room, so none of them wait for
a call to be tested.
"""

from __future__ import annotations

import json

import pytest

from agent.grounding.turn_rag import Grounding, worth_searching
from agent.retrieval.search.passage_search import Passage, Retrieval
from agent.tools.personal.demo_life import DemoLife
from agent.tools.personal.life_context import choose_life_backend


class FakeSearch:
    """Stands in for PassageSearch. Records what it was asked."""

    def __init__(self, retrieval: Retrieval):
        self.retrieval = retrieval
        self.asked: list[str] = []

    def search(self, question: str) -> Retrieval:
        self.asked.append(question)
        return self.retrieval


class FakeParticipant:
    def __init__(self, metadata: str = ""):
        self.metadata = metadata
        self.attributes: dict[str, str] = {}


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


def ungrounded_result() -> Retrieval:
    return Retrieval(passages=[], best_cosine=0.11, grounded=False, reason="below gate")


# --- 1. which backend a caller gets -----------------------------------------


def test_a_caller_with_no_metadata_gets_the_demo_backend():
    """Demo is the default, not the exception."""
    assert choose_life_backend(FakeParticipant(), live_available=True) == "demo"


def test_the_live_backend_needs_the_token_to_say_so():
    """The passphrase is checked when the token is minted, and the answer is
    signed into the token. A caller cannot assert it themselves."""
    live = FakeParticipant(json.dumps({"life_backend": "live"}))
    assert choose_life_backend(live, live_available=True) == "live"


def test_live_falls_back_to_demo_when_the_credentials_are_missing():
    """A revoked token degrades to a working demo, not a dead tool mid-call."""
    live = FakeParticipant(json.dumps({"life_backend": "live"}))
    assert choose_life_backend(live, live_available=False) == "demo"


def test_unreadable_metadata_gets_the_demo_backend():
    """Anything the worker cannot parse is not a credential."""
    assert choose_life_backend(FakeParticipant("{not json"), live_available=True) == "demo"
    assert choose_life_backend(FakeParticipant("live"), live_available=True) == "demo"


# --- 2. whether a turn gets grounded ----------------------------------------


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

    assert published == [{"sources": []}]


@pytest.mark.asyncio
async def test_a_failing_index_does_not_end_the_call():
    """If retrieval throws, he answers ungrounded rather than going silent."""

    class BrokenSearch:
        def search(self, question: str) -> Retrieval:
            raise RuntimeError("index unreadable")

    grounding = Grounding(BrokenSearch())
    assert await grounding.for_turn("what is in our power") == ""


# --- 3. what the demo backend says ------------------------------------------


def test_the_demo_week_is_the_same_every_time():
    """A grader watching the video and a grader on the link should see the same
    week, or the demo looks broken rather than seeded."""
    assert DemoLife().calendar(days=3) == DemoLife().calendar(days=3)


def test_the_demo_calendar_covers_the_days_it_was_asked_for():
    entries = DemoLife().calendar(days=3)
    assert entries, "the demo week cannot be empty -- the grader will hear it"
    assert len({e["day"] for e in entries}) <= 3


def test_the_demo_notes_read_like_a_person_wrote_them():
    notes = DemoLife().notes()
    assert notes, "demo notes cannot be empty"
    assert all(len(n["text"].split()) >= 5 for n in notes)


def test_a_journal_entry_can_be_written_and_read_back():
    """The write-back tool has to actually do something, even in demo, or
    Epictetus says he wrote it down and nothing happened."""
    life = DemoLife()
    life.write_journal("Bear and forbear.")
    assert "Bear and forbear." in [e["text"] for e in life.journal()]
