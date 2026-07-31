"""The proof page receives an honest event for every RAG decision path."""

from __future__ import annotations

import json

import pytest

from agent.grounding.turn_rag import Grounding
from agent.retrieval.search.passage_search import Passage, Retrieval


class FakeSearch:
    def __init__(self, retrieval: Retrieval):
        self.retrieval = retrieval

    def search(self, question: str) -> Retrieval:
        return self.retrieval


class FakeTurnFilter:
    def __init__(self, decision: bool = True, error: Exception | None = None):
        self.decision = decision
        self.error = error

    async def should_retrieve(self, prior_assistant: str, current_user: str) -> bool:
        if self.error is not None:
            raise self.error
        return self.decision


def retrieval(score: float, *, grounded: bool = True) -> Retrieval:
    passage = Passage(
        text="Of things some are in our power, and others are not.",
        citation="Book 1, Chapter 1",
        book=1,
        chapter=1,
        title="Of the things which are in our power",
        page=3,
        cosine=score,
        fused_score=0.03,
    )
    return Retrieval(
        passages=[passage] if grounded else [],
        best_cosine=score,
        grounded=grounded,
        reason="above minimum" if grounded else "below minimum",
    )


async def run_turn(
    result: Retrieval,
    *,
    turn_filter: FakeTurnFilter | None = None,
    hide_filter_errors: bool = False,
) -> dict:
    published: list[dict] = []

    async def publish(payload: str, topic: str) -> None:
        assert topic == Grounding.PANEL_TOPIC
        published.append(json.loads(payload))

    grounding = Grounding(
        FakeSearch(result),
        publish=publish,
        turn_filter=turn_filter,
        hide_filter_errors=hide_filter_errors,
    )
    await grounding.for_turn(
        "How should I handle this decision?",
        prior_assistant="Which choice is actually yours?",
    )
    assert len(published) == 1
    return published[0]


def assert_boundaries(rag: dict) -> None:
    assert rag["minimumCosine"] == 0.2315
    assert rag["automaticCosine"] == 0.36


@pytest.mark.asyncio
async def test_strong_match_publishes_an_automatic_grounding_decision():
    body = await run_turn(retrieval(0.51))

    assert body["sources"][0]["citation"] == "Book 1, Chapter 1"
    assert body["rag"] == {
        "status": "grounded",
        "method": "vector + BM25, merged by reciprocal rank fusion",
        "bestCosine": 0.51,
        "minimumCosine": 0.2315,
        "automaticCosine": 0.36,
        "decision": "accepted automatically",
        "reason": "above minimum",
        "selected": 1,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filter_decision", "status", "decision", "selected"),
    [
        (True, "grounded", "Luna approved", 1),
        (False, "rejected", "Luna rejected", 0),
    ],
)
async def test_luna_range_publishes_its_real_decision(
    filter_decision: bool,
    status: str,
    decision: str,
    selected: int,
):
    body = await run_turn(
        retrieval(0.2451),
        turn_filter=FakeTurnFilter(decision=filter_decision),
    )

    assert body["rag"]["status"] == status
    assert body["rag"]["decision"] == decision
    assert body["rag"]["bestCosine"] == 0.2451
    assert body["rag"]["selected"] == selected
    assert_boundaries(body["rag"])
    assert len(body["sources"]) == selected


@pytest.mark.asyncio
async def test_below_floor_publishes_a_rejection_without_calling_luna():
    body = await run_turn(
        retrieval(0.11, grounded=False),
        turn_filter=FakeTurnFilter(error=AssertionError("Luna should not run")),
    )

    assert body["sources"] == []
    assert body["rag"]["status"] == "rejected"
    assert body["rag"]["decision"] == "below minimum cosine"
    assert_boundaries(body["rag"])


@pytest.mark.asyncio
async def test_production_luna_error_is_visible_but_does_not_expose_the_exception():
    body = await run_turn(
        retrieval(0.2451),
        turn_filter=FakeTurnFilter(error=TimeoutError("secret provider detail")),
        hide_filter_errors=True,
    )

    assert body["sources"] == []
    assert body["rag"]["status"] == "error"
    assert body["rag"]["decision"] == "Luna error"
    assert "answered without passages" in body["rag"]["reason"]
    assert "secret provider detail" not in json.dumps(body)
    assert_boundaries(body["rag"])
