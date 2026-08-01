"""Logs keep operational facts without retaining a caller's words."""

from __future__ import annotations

import logging

import pytest
import tavily
from llama_index.core.schema import NodeWithScore, TextNode

from agent.grounding.turn_rag import Grounding
from agent.retrieval.search.passage_search import PassageSearch
from agent.tools.modern_world import web_search


class _Embedding:
    def get_query_embedding(self, _question: str) -> list[float]:
        return [0.1]


class _Retriever:
    def __init__(self, hits: list[NodeWithScore]):
        self._hits = hits

    def retrieve(self, _bundle) -> list[NodeWithScore]:
        return self._hits


def test_retrieval_logs_the_turn_shape_without_the_callers_words(caplog):
    private_turn = "my manager may fire me after the review tomorrow"
    node = TextNode(
        id_="book-1-chapter-1",
        text="Some things are in our power and others are not.",
        metadata={
            "citation": "Book 1, Chapter 1",
            "book": 1,
            "chapter": 1,
            "title": "Of the things which are in our power",
            "page": 3,
        },
    )
    hit = NodeWithScore(node=node, score=0.51)
    search = PassageSearch.__new__(PassageSearch)
    search._embed_model = _Embedding()
    search._vector = _Retriever([hit])
    search._bm25 = _Retriever([hit])

    with caplog.at_level(logging.DEBUG):
        result = search.search(private_turn)

    assert result.grounded is True
    assert private_turn not in caplog.text
    assert f"question_chars={len(private_turn)}" in caplog.text


@pytest.mark.asyncio
async def test_short_turn_log_keeps_the_shape_without_the_callers_words(caplog):
    private_turn = "okay thanks"
    grounding = Grounding(search=None)

    with caplog.at_level(logging.DEBUG):
        result = await grounding.for_turn(private_turn)

    assert result == ""
    assert private_turn not in caplog.text
    assert f"turn_chars={len(private_turn)}" in caplog.text


@pytest.mark.parametrize("outcome", ["success", "empty", "error"])
def test_web_search_logs_the_query_shape_without_the_callers_words(
    outcome,
    monkeypatch,
    caplog,
):
    private_query = "how do performance reviews work at my employer"

    class Client:
        def search(self, **_kwargs):
            if outcome == "error":
                raise RuntimeError("search backend unavailable")
            if outcome == "empty":
                return {"answer": "", "results": []}
            return {"answer": "A performance review is a structured evaluation.", "results": []}

    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(tavily, "TavilyClient", lambda api_key: Client())

    with caplog.at_level(logging.INFO):
        web_search.look_up(private_query)

    assert private_query not in caplog.text
    assert f"query_chars={len(private_query)}" in caplog.text
