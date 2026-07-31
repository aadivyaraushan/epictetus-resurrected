"""Hybrid search over the Discourses, with a relevance gate.

Input:  a question in plain text
Output: a Retrieval -- the passages worth showing, each with its book/chapter
        citation, plus the scores that decided whether to show anything at all

Steps:
  1. Embed the question once.
  2. Retrieve a wide first pass from both sides: vector search for meaning,
     BM25 for exact words.
  3. Merge the two rankings with reciprocal rank fusion -- arithmetic on the two
     result lists, no reranking model, no extra network call, no bill.
  4. Cap how many chunks any one chapter may contribute.
  5. Keep the top few.
  6. Decide whether they are relevant enough to use at all.

Why vector and keyword together (plan section 3): vector search alone misses
proper nouns and rare words, and the question this agent is graded on is a
specific fact -- often naming a person or an unusual term. That is where the
keyword side wins. Meanwhile a question phrased in modern English about an idea
Epictetus names differently is where the vector side wins. Neither alone is
enough.

A note on the gate, because this differs from the written plan. The plan said
to gate on "the best fusion score". Reciprocal rank fusion scores describe rank,
not relevance -- the top result scores about the same whether it is a perfect
match or the least-bad of 500 irrelevant chunks, so gating on it would not
actually gate anything. The gate here uses the raw cosine similarity from the
vector side, which does carry a relevance signal. That is also why the fusion
arithmetic is written out below instead of using LlamaIndex's
QueryFusionRetriever: the framework's fused output discards the component
scores, and those component scores are precisely what the gate needs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from llama_index.core import QueryBundle, VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore
from llama_index.retrievers.bm25 import BM25Retriever

log = logging.getLogger("retrieval.search")

# Wide first pass so the right chunk is in the pool at all...
CANDIDATES_PER_SIDE = 12
# ...then keep only what a voice turn can afford to put in the prompt. Every
# extra chunk is more tokens before the first spoken word.
KEEP_TOP = 4
# One chapter cannot supply more than this. Three chapters in the Discourses run
# past 3,000 words and produce a lot of chunks; without a cap, one long chapter
# can fill the whole pool and crowd out the chapter that actually answers.
MAX_PER_CHAPTER = 2

# Reciprocal rank fusion's smoothing constant. 60 is the value from the original
# paper and the usual default; it keeps any single list from dominating.
RRF_K = 60

# Below this cosine similarity we treat the corpus as having nothing to say and
# hand the model no passages. Matches from this floor up to the old 0.36 gate
# receive a separate dialogue-intent check in turn_rag.py.
#
# Measured, not guessed, and the measurement is worth reading before anyone
# moves this number. Two question sets, both in eval/:
#
#   questions.json         53 questions generated from the chapters. Every one
#                          scores 0.494 or higher -- they borrow the chapter's
#                          own vocabulary, so they look easy.
#   spoken_questions.json  12 written by hand as a person would say them out
#                          loud, no borrowed words. These score 0.19 to 0.50.
#
# The first set alone suggests a comfortable threshold around 0.42. The second
# set shows that is wrong: real spoken questions reach down into the range where
# small talk lives, and no threshold separates the two populations cleanly.
#
# A production conversation exposed five logically relevant turns below 0.36.
# The weakest was a decision to walk away at 0.2315014467, so 0.2315 is the
# highest four-decimal floor that retains it. Cosine alone cannot reject the
# closing acknowledgment in that same conversation: it scored 0.2451. The
# Luna check handles that overlapping range instead of pretending one number
# separates dialogue intent from topic similarity.
#
# The old 0.36 gate remains the automatic-accept boundary. This module reports
# matches from 0.2315 upward; turn_rag.py asks Luna about only the newly admitted
# 0.2315-to-0.36 range. In the measured conversation that retained five required
# turns, rejected its closing thanks, and rejected three tool/small-talk controls.
#
# Things that were tried and did not work: gating on how far the best chunk
# beats the rest of the candidate pool (margin, gap between first and second,
# or ratio to the pool mean). The idea was that a corpus of one author on one
# subject is mildly close to any philosophical question, so a standout chunk
# should matter more than an absolute score. The numbers say the opposite --
# small talk shows a *larger* margin than real questions, because its candidates
# are uniformly poor. Raw cosine separates far better than any of them.
MIN_COSINE_TO_GROUND = 0.2315


@dataclass(frozen=True)
class Passage:
    text: str
    citation: str  # "Book 2, Chapter 5" -- what the source panel shows
    book: int
    chapter: int
    title: str
    page: int
    cosine: float  # raw vector similarity, kept for the gate and for debugging
    fused_score: float

    def as_panel_entry(self) -> dict:
        """The shape sent to the browser over the LiveKit data channel."""
        return {
            "citation": self.citation,
            "title": self.title,
            "book": self.book,
            "chapter": self.chapter,
            "page": self.page,
            "text": self.text,
            "score": round(self.cosine, 4),
        }


@dataclass(frozen=True)
class Retrieval:
    passages: list[Passage] = field(default_factory=list)
    best_cosine: float = 0.0
    grounded: bool = False  # did the gate let the passages through?
    reason: str = ""

    def prompt_block(self) -> str:
        """The passages as the LLM sees them.

        Deliberately unnumbered and uncited. Epictetus does not say "as I wrote
        in Book II" -- he speaks, and the panel cites. Handing the model chapter
        numbers is handing it something to read aloud.
        """
        if not self.grounded or not self.passages:
            return ""
        parts = [p.text.strip() for p in self.passages]
        return (
            "Some of your own recorded teaching, for your reference. Speak from "
            "it in your own voice; never mention books, chapters, or that you "
            "are consulting anything.\n\n" + "\n\n---\n\n".join(parts)
        )


class PassageSearch:
    """Loaded once when the worker starts; queried on every user turn."""

    def __init__(self, index: VectorStoreIndex):
        self._embed_model = index._embed_model
        self._vector = VectorIndexRetriever(
            index=index,
            similarity_top_k=CANDIDATES_PER_SIDE,
            embed_model=self._embed_model,
        )
        self._bm25 = BM25Retriever.from_defaults(
            docstore=index.docstore,
            similarity_top_k=CANDIDATES_PER_SIDE,
        )
        log.info(
            "[retrieval.search] ready: %d candidates per side, keep %d, cap %d per chapter",
            CANDIDATES_PER_SIDE,
            KEEP_TOP,
            MAX_PER_CHAPTER,
        )

    def search(self, question: str) -> Retrieval:
        question = (question or "").strip()
        if not question:
            return Retrieval(reason="empty question")

        # Embed once and hand the same vector to the vector retriever, rather
        # than letting each side embed the question again. On a voice call that
        # saves a network round-trip in the middle of the response.
        bundle = QueryBundle(query_str=question)
        bundle.embedding = self._embed_model.get_query_embedding(question)

        vector_hits = self._vector.retrieve(bundle)
        keyword_hits = self._bm25.retrieve(bundle)

        log.debug(
            "[retrieval.search] %r -> %d vector, %d keyword candidates",
            question[:60],
            len(vector_hits),
            len(keyword_hits),
        )

        cosine_by_id = {hit.node.node_id: float(hit.score or 0.0) for hit in vector_hits}
        fused = _reciprocal_rank_fusion(vector_hits, keyword_hits)
        kept = _cap_per_chapter(fused, MAX_PER_CHAPTER)[:KEEP_TOP]

        passages = [
            Passage(
                text=hit.node.get_content(),
                citation=hit.node.metadata.get("citation", ""),
                book=int(hit.node.metadata.get("book", 0)),
                chapter=int(hit.node.metadata.get("chapter", 0)),
                title=hit.node.metadata.get("title", ""),
                page=int(hit.node.metadata.get("page", 0)),
                cosine=cosine_by_id.get(hit.node.node_id, 0.0),
                fused_score=float(hit.score or 0.0),
            )
            for hit in kept
        ]

        best_cosine = max(cosine_by_id.values(), default=0.0)
        grounded = best_cosine >= MIN_COSINE_TO_GROUND

        reason = (
            f"best cosine {best_cosine:.3f} >= {MIN_COSINE_TO_GROUND}"
            if grounded
            else f"best cosine {best_cosine:.3f} < {MIN_COSINE_TO_GROUND}, not grounding this turn"
        )
        log.info(
            "[retrieval.search] %r -> %s | %s",
            question[:60],
            [p.citation for p in passages] if grounded else "no passages",
            reason,
        )

        return Retrieval(
            passages=passages if grounded else [],
            best_cosine=best_cosine,
            grounded=grounded,
            reason=reason,
        )


def _reciprocal_rank_fusion(
    *rankings: list[NodeWithScore],
) -> list[NodeWithScore]:
    """Merge ranked lists by position, not by score.

    Each list contributes 1/(k + rank) for every chunk it ranks, and the
    contributions are added up. Using position rather than score is the point:
    a cosine similarity and a BM25 score are on different scales and cannot be
    added together meaningfully, but "third in one list and first in the other"
    is comparable across both.
    """
    totals: dict[str, float] = {}
    nodes: dict[str, NodeWithScore] = {}

    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            node_id = hit.node.node_id
            totals[node_id] = totals.get(node_id, 0.0) + 1.0 / (RRF_K + rank)
            nodes.setdefault(node_id, hit)

    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return [NodeWithScore(node=nodes[node_id].node, score=score) for node_id, score in ordered]


def _cap_per_chapter(hits: list[NodeWithScore], cap: int) -> list[NodeWithScore]:
    """Let no single chapter fill the pool, keeping the ranking otherwise intact."""
    seen: dict[tuple[int, int], int] = {}
    kept: list[NodeWithScore] = []
    for hit in hits:
        key = (hit.node.metadata.get("book"), hit.node.metadata.get("chapter"))
        if seen.get(key, 0) >= cap:
            continue
        seen[key] = seen.get(key, 0) + 1
        kept.append(hit)
    return kept
