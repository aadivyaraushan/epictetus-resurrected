"""The agent's decisions, tested without a microphone.

Three things in the worker make a decision that can be wrong in a way nobody
would notice on a call:

  1. Which personal backend a caller gets. Getting this wrong means a stranger
     on a public link reads my real notes (plan section 4).
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


def test_the_live_backend_reads_the_key_name_that_is_actually_in_the_env(monkeypatch):
    """The env file names this key NOTION_API_KEY, like every other vendor key
    here. If the code reads a different name, nothing errors -- the live backend
    just silently reports itself unconfigured and every caller lands on the demo
    notes, including me with a valid token sitting right there."""
    from agent.tools.personal.live_life import _notion_headers, live_credentials_present

    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    monkeypatch.setenv("NOTION_API_KEY", "secret_abc123")

    assert live_credentials_present() is True
    assert _notion_headers()["Authorization"] == "Bearer secret_abc123"


def test_no_notion_key_means_no_live_backend(monkeypatch):
    from agent.tools.personal.live_life import live_credentials_present

    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    assert live_credentials_present() is False


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


# --- 3. which tools exist at all ---------------------------------------------


EXPECTED_TOOLS = {"look_up_modern_thing", "search_my_notion", "write_to_session_log"}


def test_the_agent_exposes_exactly_the_three_planned_tools():
    """Plan section 4. A tool that is registered but half-removed still shows up
    in the LLM's tool list, so it can still be called mid-call and fail."""
    from agent.persona.epictetus_agent import Epictetus

    registered = {
        name
        for name in dir(Epictetus)
        if getattr(getattr(Epictetus, name, None), "__livekit_tool_info", None) is not None
    }
    assert registered == EXPECTED_TOOLS


def test_nothing_reads_a_calendar_any_more():
    """Google Calendar was cut (plan section 4). The tool, the protocol method
    and both backends go together -- leaving the backend behind is how a dead
    code path survives a deletion."""
    from agent.persona.epictetus_agent import Epictetus
    from agent.tools.personal.life_context import LifeContext, LifeSource

    assert not hasattr(Epictetus, "read_my_calendar")
    assert not hasattr(LifeSource, "calendar")
    assert not hasattr(DemoLife(), "calendar")
    assert "calendar" not in LifeContext.__protocol_attrs__


# --- 4. what the demo backend says ------------------------------------------


def test_the_demo_week_is_the_same_every_time():
    """A grader watching the video and a grader on the link should see the same
    notes, or the demo looks broken rather than seeded."""
    assert DemoLife().search_notes("work") == DemoLife().search_notes("work")


def test_the_demo_notes_read_like_a_person_wrote_them():
    notes = DemoLife().search_notes("review")
    assert notes, "demo notes cannot be empty"
    assert all(len(n["text"].split()) >= 5 for n in notes)


def test_searching_the_demo_notes_narrows_them():
    """If every query returned the whole set, the search tool would be a fixed
    read wearing a query parameter."""
    everything = DemoLife().search_notes("")
    about_sophia = DemoLife().search_notes("Sophia")
    assert len(about_sophia) < len(everything)
    assert all("sophia" in n["text"].lower() for n in about_sophia)


def test_a_demo_search_that_matches_nothing_still_says_something():
    """An empty answer reads as a broken tool on a call, not an honest miss."""
    assert DemoLife().search_notes("xylophone quarterly velocipede") == DemoLife().search_notes("")


def test_a_session_log_entry_can_be_written_and_read_back():
    """The write-back tool has to actually do something, even in demo, or
    Epictetus says he wrote it down and nothing happened."""
    life = DemoLife()
    life.write_session_log("Bear and forbear.")
    assert "Bear and forbear." in [e["text"] for e in life.session_log()]


def test_the_session_log_starts_empty():
    """This is the whole reason it is a session log and not a journal. Nothing
    is seeded, so a non-empty log is proof the write tool fired on this call --
    there is no other way for a line to get in there."""
    assert DemoLife().session_log() == []


def test_a_written_entry_is_numbered_so_he_can_say_it_out_loud():
    """"That is the third thing I have written down" is checkable by a listener
    in a way that "I have written it down" is not."""
    life = DemoLife()
    assert life.write_session_log("first")["entry"] == 1
    assert life.write_session_log("second")["entry"] == 2


def test_an_empty_entry_is_refused_rather_than_written():
    """A blank line in the log would look like a write that worked."""
    with pytest.raises(ValueError):
        DemoLife().write_session_log("   ")


def test_nothing_keeps_a_journal_any_more():
    """The journal became the session log (see the tool's docstring). Tool,
    protocol method and both backends move together -- a half-finished rename
    leaves a method that still works and is never called, which is worse than
    one that is gone."""
    from agent.persona.epictetus_agent import Epictetus
    from agent.tools.personal.life_context import LifeContext, LifeSource
    from agent.tools.personal.live_life import LiveLife

    assert not hasattr(Epictetus, "write_to_journal")
    assert not hasattr(LifeSource, "write_journal")
    assert not hasattr(DemoLife(), "write_journal")
    assert not hasattr(LiveLife, "write_journal")
    assert "write_journal" not in LifeContext.__protocol_attrs__
