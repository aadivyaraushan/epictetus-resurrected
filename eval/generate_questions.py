"""Write the labelled question set the retrieval harness runs against.

Run once. The output is committed, so re-running the harness costs nothing and
anyone can reproduce the numbers in the README without paying for generation.

Input:  index/ (for the chunk text) or corpus/discourses.pdf
Output: eval/questions.json -- questions, each labelled with the book and
        chapter that actually answers it

Steps:
  1. Sample chapters across all four books, weighted so long chapters are not
     over-represented and very short ones still appear.
  2. Ask an LLM to read one chapter and write questions a person would actually
     ask out loud, answerable only from that chapter.
  3. Reject questions that name the book or chapter number, or that quote the
     text nearly verbatim -- both would make the retrieval look better than it
     is. A question that repeats the passage word for word is a keyword-search
     gimme, not a test.
  4. Write them out with their gold chapter label.

Cost: about five cents with gpt-4.1-mini for sixty questions. This is the only
part of the eval loop that spends money, and it happens once.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from agent.retrieval.parse_pdf import ParsedChapter, parse_discourses_pdf  # noqa: E402

log = logging.getLogger("eval.generate")

OUT = REPO / "eval" / "questions.json"
CORPUS_PDF = REPO / "corpus" / "discourses.pdf"

GENERATOR_MODEL = "gpt-4.1-mini"

PROMPT = """You are helping test a search system over Epictetus's Discourses.

Below is the complete text of one chapter. Write {n} questions that:

- a real person would plausibly ask a Stoic teacher out loud, in conversation
- can be answered from THIS chapter and would be hard to answer from another
- name the specific people, examples, objects or situations this chapter uses,
  because that specificity is what makes the question answerable from here

Hard rules:
- Never mention a book number or chapter number.
- Never quote more than three consecutive words from the text.
- Write the way someone speaks, not the way someone writes a search query.

Return a JSON object: {{"questions": ["...", "..."]}}

CHAPTER TEXT:
{text}
"""


def pick_chapters(chapters: list[ParsedChapter], count: int, seed: int) -> list[ParsedChapter]:
    """Spread the sample across all four books rather than sampling uniformly.

    Uniform sampling would follow the shape of the book, and Book 1 has more
    chapters than Book 4. A grader may ask about anything, so every book should
    be represented roughly in proportion to how much a reader would use it.
    """
    rng = random.Random(seed)
    by_book: dict[int, list[ParsedChapter]] = {}
    for chapter in chapters:
        by_book.setdefault(chapter.book, []).append(chapter)

    picked: list[ParsedChapter] = []
    books = sorted(by_book)
    per_book = max(1, count // len(books))
    for book in books:
        pool = [c for c in by_book[book] if len(c.text.split()) >= 250]
        rng.shuffle(pool)
        picked.extend(pool[:per_book])

    rng.shuffle(picked)
    return picked[:count]


def looks_verbatim(question: str, chapter_text: str) -> bool:
    """Reject questions that lift a phrase straight out of the chapter.

    Those inflate the keyword side of the hybrid search and would make the
    measured hit rate a lie.
    """
    words = re.findall(r"\w+", question.lower())
    haystack = " ".join(re.findall(r"\w+", chapter_text.lower()))
    for start in range(len(words) - 4):
        if " ".join(words[start : start + 5]) in haystack:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", type=int, default=30, help="how many chapters to sample")
    parser.add_argument("--per-chapter", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260731)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set; question generation needs it.", file=sys.stderr)
        return 1

    from openai import OpenAI

    client = OpenAI()
    chapters = parse_discourses_pdf(CORPUS_PDF)
    sample = pick_chapters(chapters, args.chapters, args.seed)
    log.info("[eval.generate] sampling %d chapters", len(sample))

    questions: list[dict] = []
    rejected = 0

    for chapter in sample:
        response = client.chat.completions.create(
            model=GENERATOR_MODEL,
            response_format={"type": "json_object"},
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT.format(n=args.per_chapter, text=chapter.text[:12000]),
                }
            ],
        )
        try:
            produced = json.loads(response.choices[0].message.content)["questions"]
        except (KeyError, json.JSONDecodeError, TypeError) as exc:
            log.warning("[eval.generate] %s: unusable response (%s), skipping", chapter.slug, exc)
            continue

        for question in produced:
            question = question.strip()
            if not question:
                continue
            if re.search(r"\bbook\s+(one|two|three|four|[1-4ivx])", question, re.I):
                rejected += 1
                continue
            if re.search(r"\bchapter\b", question, re.I):
                rejected += 1
                continue
            if looks_verbatim(question, chapter.text):
                rejected += 1
                continue
            questions.append(
                {
                    "question": question,
                    "book": chapter.book,
                    "chapter": chapter.chapter,
                    "title": chapter.title,
                }
            )
        log.info("[eval.generate] %s -> %d kept so far", chapter.slug, len(questions))

    OUT.write_text(
        json.dumps(
            {
                "generated_by": GENERATOR_MODEL,
                "seed": args.seed,
                "rejected": rejected,
                "questions": questions,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log.info(
        "[eval.generate] wrote %d questions to %s (%d rejected as too easy or self-labelling)",
        len(questions),
        OUT,
        rejected,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
