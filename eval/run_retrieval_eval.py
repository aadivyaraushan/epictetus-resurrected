"""Measure whether the right chapter comes back, before any voice is involved.

The brief says a grader will ask about a specific fact in a specific chapter.
This harness asks that question sixty times against the saved index and counts
how often the right chapter is in the results.

Input:  eval/questions.json -- questions each labelled with the chapter that
        actually answers them
        index/ -- the built index
Output: hit rates printed to the terminal, and optionally a JSON report

Steps:
  1. Load the index once.
  2. Ask every question, record which chapters came back and in what order.
  3. Count how often the right chapter is first, in the top 3, in the top 4.
  4. Ask a set of small-talk questions too, and record their scores -- these are
     the noise floor the relevance gate has to sit above.

One run costs one embedding call per question and no LLM calls at all, so it
takes seconds. That is the point: parameters get tuned against measurements, and
tuning is only worth doing if a measurement is cheap. Nothing here spends money
beyond a fraction of a cent of embeddings.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from agent.retrieval.search import passage_search  # noqa: E402
from agent.retrieval.search.index_store import load_index  # noqa: E402
from agent.retrieval.search.passage_search import PassageSearch  # noqa: E402

log = logging.getLogger("eval.retrieval")

QUESTIONS = REPO / "eval" / "questions.json"

# Turns that should NOT drag philosophy into the conversation. Their scores show
# which controls reach the Luna range; the final decision is no longer made by
# raw cosine alone.
SMALL_TALK = [
    "hey, can you hear me?",
    "hello",
    "sorry, one second",
    "what's on my calendar tomorrow?",
    "can you write that down in my journal?",
    "yeah, exactly",
    "okay, thanks",
    "wait, say that again?",
    "what time is it",
    "cool",
    "um, hold on",
    "can you look up what a smartphone is",
]


def evaluate(search: PassageSearch, questions: list[dict], top_k: int) -> dict:
    hits_at = {1: 0, 3: 0, 4: 0}
    reciprocal_ranks: list[float] = []
    misses: list[dict] = []
    cosines: list[float] = []
    latencies: list[float] = []

    for item in questions:
        gold = (item["book"], item["chapter"])
        started = time.perf_counter()
        result = search.search(item["question"])
        latencies.append((time.perf_counter() - started) * 1000)
        cosines.append(result.best_cosine)

        chapters = [(p.book, p.chapter) for p in result.passages]
        # A chapter can supply more than one chunk; rank by first appearance.
        ordered: list[tuple[int, int]] = []
        for chapter in chapters:
            if chapter not in ordered:
                ordered.append(chapter)

        if gold in ordered:
            rank = ordered.index(gold) + 1
            reciprocal_ranks.append(1.0 / rank)
            for cutoff in hits_at:
                if rank <= cutoff:
                    hits_at[cutoff] += 1
        else:
            reciprocal_ranks.append(0.0)
            misses.append(
                {
                    "question": item["question"],
                    "expected": f"Book {gold[0]}, Chapter {gold[1]}",
                    "got": [f"B{b}C{c}" for b, c in ordered],
                    "best_cosine": round(result.best_cosine, 4),
                }
            )

    total = len(questions) or 1
    return {
        "questions": len(questions),
        "top_k": top_k,
        "hit@1": hits_at[1] / total,
        "hit@3": hits_at[3] / total,
        "hit@4": hits_at[4] / total,
        "mrr": sum(reciprocal_ranks) / total,
        "cosine_min": min(cosines, default=0.0),
        "cosine_median": sorted(cosines)[len(cosines) // 2] if cosines else 0.0,
        "cosines": cosines,
        # Paired with the question, weakest first: the gate is only as good as
        # its worst real question, and it helps to see which one that is.
        "cosine_by_question": sorted(
            ((round(c, 4), q["question"]) for c, q in zip(cosines, questions)),
        ),
        "latency_ms_median": sorted(latencies)[len(latencies) // 2] if latencies else 0.0,
        "misses": misses,
    }


def gate_check(search: PassageSearch, real_cosines: list[float]) -> dict:
    """Which turns reach the raw floor before the dialogue-intent check."""
    small_talk_cosines = [search.search(turn).best_cosine for turn in SMALL_TALK]
    return {
        "small_talk_max": max(small_talk_cosines, default=0.0),
        "small_talk_median": (
            sorted(small_talk_cosines)[len(small_talk_cosines) // 2] if small_talk_cosines else 0.0
        ),
        "real_question_min": min(real_cosines, default=0.0),
        "current_threshold": passage_search.MIN_COSINE_TO_GROUND,
        "per_turn": dict(zip(SMALL_TALK, [round(c, 4) for c in small_talk_cosines])),
    }


class _NoHits:
    """A retriever that finds nothing, for measuring one side on its own.

    The plan asserts that hybrid search beats either half. That is a claim about
    this corpus, and it is cheap to check, so `--only vector` and `--only
    keyword` turn one side off and the numbers settle it. Done here rather than
    with a switch in passage_search.py, because the agent should have no
    retrieval parameters it can get wrong at runtime.
    """

    def retrieve(self, _bundle):
        return []


def use_only(search: PassageSearch, side: str) -> None:
    """Turn one half off, to measure the other on its own."""
    if side == "vector":
        search._bm25 = _NoHits()
    elif side == "keyword":
        search._vector = _NoHits()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        choices=["vector", "keyword"],
        help="measure one half of the hybrid on its own",
    )
    parser.add_argument("--top-k", type=int, default=passage_search.KEEP_TOP)
    parser.add_argument("--candidates", type=int, default=passage_search.CANDIDATES_PER_SIDE)
    parser.add_argument("--max-per-chapter", type=int, default=passage_search.MAX_PER_CHAPTER)
    parser.add_argument(
        "--questions",
        type=Path,
        default=QUESTIONS,
        help="which question set to run (see eval/spoken_questions.json)",
    )
    parser.add_argument("--report", type=Path, help="write the full result as JSON here")
    parser.add_argument("--show-misses", type=int, default=8)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    if not args.questions.exists():
        print(
            f"No question set at {args.questions}.\n"
            f"Generate one with: python eval/generate_questions.py",
            file=sys.stderr,
        )
        return 1

    questions = json.loads(args.questions.read_text(encoding="utf-8"))["questions"]

    # Tuning knobs are module-level constants so the agent has no parameters to
    # get wrong at runtime; the harness overrides them in-process for a sweep.
    passage_search.KEEP_TOP = args.top_k
    passage_search.CANDIDATES_PER_SIDE = args.candidates
    passage_search.MAX_PER_CHAPTER = args.max_per_chapter

    search = PassageSearch(load_index())
    if args.only:
        use_only(search, args.only)

    # Two separate questions, measured separately.
    #
    # 1. Ranking: does the right chapter come back, and how high? The gate has no
    #    business here -- a gated-out turn returns an empty list, which counts as
    #    a ranking miss when nothing was actually mis-ranked. Worse, the gate
    #    reads cosine similarity, which only the vector side produces, so leaving
    #    it on makes keyword-only score zero on everything for a reason that has
    #    nothing to do with BM25. Off for every mode, so all three are comparable.
    # 2. The gate: where should the threshold sit? That is gate_check below,
    #    which reads the raw cosines and does not care about ranking at all.
    threshold = passage_search.MIN_COSINE_TO_GROUND
    passage_search.MIN_COSINE_TO_GROUND = 0.0

    result = evaluate(search, questions, args.top_k)
    result["retrievers"] = args.only or "hybrid"
    passage_search.MIN_COSINE_TO_GROUND = threshold
    result["gate"] = gate_check(search, result.pop("cosines"))

    print(
        f"\n  {result['questions']} questions | {result['retrievers']} | "
        f"candidates/side {args.candidates}, keep {args.top_k}, "
        f"cap {args.max_per_chapter} per chapter"
    )
    print(f"  hit@1  {result['hit@1']:.1%}")
    print(f"  hit@3  {result['hit@3']:.1%}")
    print(f"  hit@4  {result['hit@4']:.1%}   <- the number that matters")
    print(f"  MRR    {result['mrr']:.3f}")
    print(f"  median retrieval latency  {result['latency_ms_median']:.0f} ms")

    gate = result["gate"]
    print(
        f"\n  gate: small talk tops out at cosine {gate['small_talk_max']:.3f}; "
        f"threshold is {gate['current_threshold']}"
    )
    print(
        f"  the weakest real question scores {gate['real_question_min']:.3f}, "
        f"so the gap the threshold sits in is "
        f"{gate['small_talk_max']:.3f} .. {gate['real_question_min']:.3f}"
    )
    if gate["small_talk_max"] >= gate["current_threshold"]:
        print("  NOTE: small talk reaches the raw floor -- Luna decides final grounding")
    if gate["real_question_min"] < gate["current_threshold"]:
        print("  WARNING: a real question falls below the gate -- it would go ungrounded")

    if result["misses"]:
        print(f"\n  {len(result['misses'])} misses; first {args.show_misses}:")
        for miss in result["misses"][: args.show_misses]:
            print(f"    {miss['expected']:<22} got {miss['got']}  ({miss['best_cosine']})")
            print(f"      {miss['question']}")

    if args.report:
        args.report.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\n  wrote {args.report}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
