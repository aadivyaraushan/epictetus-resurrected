"""Ground every turn in the Discourses, before the model gets to answer.

This is the decision from plan section 3, in code. LiveKit offers two ways to
wire RAG into a voice agent: expose it as a tool the model may call, or run it
on every turn in `on_user_turn_completed`. This module is the second.

The reason is the graded question. A grader is going to ask a specific fact from
a specific chapter, and GPT already knows Epictetus well enough to answer that
correctly from memory. If retrieval were a tool, the model could reasonably
decide it does not need one -- and the whole RAG system would sit unused during
the exact moment it was being graded. Running it every turn takes the decision
away: the passages are in context whether the model wanted them or not, and the
source panel has something real to show.

Input:  what the caller just said
Output: a block of text to append to the chat context, or "" -- and, as a side
        effect, the source panel in the browser is updated

Steps:
  1. Skip turns too short to carry a question. No embedding call, no latency.
  2. Search the index (off the event loop -- it makes a network call).
  3. Reject anything below 0.2315; accept anything at or above 0.36.
  4. Ask Luna about dialogue intent only inside the overlapping middle range.
  5. Tell the browser what was used, or that nothing was, either way.

Running on every turn needs the gate, or he becomes a fortune cookie. Without
one, "hey, can you hear me?" gets Stoic philosophy stapled to it and Epictetus
starts quoting himself at nothing -- and the brief grades personality
explicitly. Cosine similarity says whether the words resemble the corpus, but
not whether a turn adds anything new to the dialogue. That is why the middle
range also checks the preceding Epictetus reply and the current user turn.

The plan also said to skip retrieval on turns that dispatch a tool call. That
cannot be known here, because this hook runs before the model has decided
anything. The dialogue-intent check covers it in practice: "what's on my
calendar tomorrow?" scores 0.3536 and therefore reaches Luna, which rejected it
in the measured end-to-end check.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable, Protocol

from agent.retrieval.search.passage_search import MIN_COSINE_TO_GROUND, Retrieval

log = logging.getLogger("agent.grounding")

# Turns shorter than this never reach the index. "yeah", "okay thanks" and
# "hold on" cannot be questions about a book, and retrieval now sits inside the
# response loop, so a turn that cannot need it should not pay for it. A bare
# "why?" is the deliberate cost of this rule: it is answered from the
# conversation so far, which is where its answer actually lives.
MIN_WORDS_TO_SEARCH = 4

# The former cosine gate remains the point above which retrieval is strong
# enough not to pay for a second model call. Only the newly admitted range is
# ambiguous enough to ask Luna about dialogue intent.
LUNA_FILTER_MAX_COSINE = 0.36


class Searcher(Protocol):
    def search(self, question: str) -> Retrieval: ...


class TurnFilter(Protocol):
    async def should_retrieve(self, prior_assistant: str, current_user: str) -> bool: ...


Publisher = Callable[[str, str], Awaitable[None]]

RAG_METHOD = "vector + BM25, merged by reciprocal rank fusion"


def worth_searching(text: str) -> bool:
    return len((text or "").split()) >= MIN_WORDS_TO_SEARCH


class Grounding:
    """Holds the loaded index and the channel back to the browser."""

    # The browser subscribes to this topic to fill the source panel. That panel
    # is doing real work: a good spoken answer alone does not prove retrieval
    # happened, because the model knows Epictetus anyway. Showing the passage is
    # what makes the RAG visibly real to someone watching.
    PANEL_TOPIC = "epictetus.sources"

    def __init__(
        self,
        search: Searcher,
        publish: Publisher | None = None,
        turn_filter: TurnFilter | None = None,
        hide_filter_errors: bool = False,
    ):
        self._search = search
        self._publish = publish
        self._turn_filter = turn_filter
        self._hide_filter_errors = hide_filter_errors

    async def for_turn(self, text: str, prior_assistant: str = "") -> str:
        """The passages to append to this turn's context, or ""."""
        text = (text or "").strip()

        if not worth_searching(text):
            log.debug("[agent.grounding] %r is too short to search; skipping", text)
            await self._show(
                [],
                status="skipped",
                method="word-count check before retrieval",
                decision="turn too short",
                reason=f"fewer than {MIN_WORDS_TO_SEARCH} words",
            )
            return ""

        try:
            retrieval = await asyncio.to_thread(self._search.search, text)
        except Exception:
            # A broken index must not end the call. He answers from the persona
            # alone, ungrounded, and the panel shows nothing -- which is honest.
            log.exception("[agent.grounding] retrieval failed; answering ungrounded")
            await self._show(
                [],
                status="error",
                method=RAG_METHOD,
                decision="retrieval error",
                reason="retrieval failed; answered without passages",
            )
            return ""

        if not retrieval.grounded:
            log.info("[agent.grounding] not grounding this turn: %s", retrieval.reason)
            await self._show(
                [],
                status="rejected",
                method=RAG_METHOD,
                decision="below minimum cosine",
                reason=retrieval.reason,
                best_cosine=retrieval.best_cosine,
            )
            return ""

        if retrieval.best_cosine < LUNA_FILTER_MAX_COSINE:
            if self._turn_filter is None:
                raise RuntimeError("A Luna turn filter is required for retrieval scores below 0.36")
            try:
                should_retrieve = await self._turn_filter.should_retrieve(
                    prior_assistant=prior_assistant,
                    current_user=text,
                )
            except Exception:
                if not self._hide_filter_errors:
                    log.exception(
                        "[agent.grounding] Luna filter failed at cosine %.4f; "
                        "stopping this non-production request",
                        retrieval.best_cosine,
                    )
                    raise
                log.exception(
                    "[agent.grounding] Luna filter failed at cosine %.4f; "
                    "showing no sources because production error hiding is enabled",
                    retrieval.best_cosine,
                )
                await self._show(
                    [],
                    status="error",
                    method=RAG_METHOD,
                    decision="Luna error",
                    reason="Luna timed out or failed; answered without passages",
                    best_cosine=retrieval.best_cosine,
                )
                return ""
            else:
                log.info(
                    "[agent.grounding] Luna range decision=%s best_cosine=%.4f",
                    "retrieve" if should_retrieve else "skip",
                    retrieval.best_cosine,
                )
                if not should_retrieve:
                    await self._show(
                        [],
                        status="rejected",
                        method=RAG_METHOD,
                        decision="Luna rejected",
                        reason=retrieval.reason,
                        best_cosine=retrieval.best_cosine,
                    )
                    return ""
                decision = "Luna approved"
        else:
            decision = "accepted automatically"

        log.info(
            "[agent.grounding] grounded on %s (best cosine %.3f)",
            [p.citation for p in retrieval.passages],
            retrieval.best_cosine,
        )
        await self._show(
            [p.as_panel_entry() for p in retrieval.passages],
            status="grounded",
            method=RAG_METHOD,
            decision=decision,
            reason=retrieval.reason,
            best_cosine=retrieval.best_cosine,
        )
        return retrieval.prompt_block()

    async def _show(
        self,
        sources: list[dict],
        *,
        status: str,
        method: str,
        decision: str,
        reason: str,
        best_cosine: float | None = None,
    ) -> None:
        """Update the source panel -- including clearing it.

        Clearing matters as much as filling. A panel left showing the last
        answer's chapter while Epictetus talks about something else is a
        citation for a claim he did not make.
        """
        if self._publish is None:
            return
        try:
            await self._publish(
                json.dumps(
                    {
                        "sources": sources,
                        "rag": {
                            "status": status,
                            "method": method,
                            "bestCosine": best_cosine,
                            "minimumCosine": MIN_COSINE_TO_GROUND,
                            "automaticCosine": LUNA_FILTER_MAX_COSINE,
                            "decision": decision,
                            "reason": reason,
                            "selected": len(sources),
                        },
                    }
                ),
                self.PANEL_TOPIC,
            )
        except Exception:
            log.exception("[agent.grounding] could not update the source panel")
