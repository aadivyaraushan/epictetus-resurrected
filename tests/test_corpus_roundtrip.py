"""The corpus round-trip check -- the first thing that has to pass.

Plan section 3 builds a clean PDF from verified Wikisource text and then parses
that PDF back out with an ordinary PDF reader, the same code path a user's
uploaded PDF would take. Everything downstream (chunking, the index, every
citation the agent speaks) inherits whatever this step produces.

So this test asks one question: does the text that comes out of the PDF still
match the text that went in, chapter for chapter, with the right labels?

If typesetting mangles a ligature, drops a paragraph, or shifts a chapter
heading, this fails here -- before the index exists, before any money is spent
on embeddings.
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

import pytest

from agent.retrieval.parse_pdf import parse_discourses_pdf

REPO = Path(__file__).resolve().parents[1]
PDF = REPO / "corpus" / "discourses.pdf"
SOURCE = REPO / "corpus" / "source"
MANIFEST = SOURCE / "manifest.json"

# The George Long translation on Wikisource: Book 1 has 30 chapters, Book 2 has
# 26, Book 3 has 26, Book 4 has 13.
EXPECTED_CHAPTERS_PER_BOOK = {1: 30, 2: 26, 3: 26, 4: 13}
EXPECTED_TOTAL = sum(EXPECTED_CHAPTERS_PER_BOOK.values())  # 95


def normalize(text: str) -> list[str]:
    """Lowercase word list, punctuation-insensitive.

    A PDF reader reflows lines, so comparing raw strings would fail on
    line breaks that carry no meaning. Comparing word sequences catches what we
    actually care about: dropped, duplicated, or corrupted words.
    """
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("—", " ").replace("–", " ")
    text = re.sub(r"[^\w\s']", " ", text.lower())
    return text.split()


@pytest.fixture(scope="module")
def parsed():
    if not PDF.exists():
        pytest.fail(
            f"{PDF} does not exist. Build it first:\n"
            f"  python corpus/build/fetch_wikisource.py\n"
            f"  python corpus/build/typeset_pdf.py"
        )
    return parse_discourses_pdf(PDF)


@pytest.fixture(scope="module")
def manifest():
    if not MANIFEST.exists():
        pytest.fail(f"{MANIFEST} missing. Run: python corpus/build/fetch_wikisource.py")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_every_chapter_survives_the_pdf(parsed):
    """95 chapters go in; 95 chapters come out, none of them empty."""
    assert len(parsed) == EXPECTED_TOTAL, (
        f"expected {EXPECTED_TOTAL} chapters out of the PDF, got {len(parsed)}"
    )
    empty = [f"B{c.book}C{c.chapter}" for c in parsed if not c.text.strip()]
    assert not empty, f"chapters parsed out empty: {empty}"


def test_book_and_chapter_labels_are_right(parsed):
    """Labels are what the agent cites, so a wrong one is a wrong citation."""
    found = {(c.book, c.chapter) for c in parsed}
    expected = {
        (book, chapter)
        for book, count in EXPECTED_CHAPTERS_PER_BOOK.items()
        for chapter in range(1, count + 1)
    }
    assert found == expected, (
        f"missing: {sorted(expected - found)}\nunexpected: {sorted(found - expected)}"
    )


def test_chapters_come_out_in_reading_order(parsed):
    order = [(c.book, c.chapter) for c in parsed]
    assert order == sorted(order), "chapters are out of order in the parsed output"


def test_no_chapter_absorbed_its_neighbour(parsed, manifest):
    """A heading the parser misses would silently merge two chapters into one.

    That is the failure that would produce confidently wrong citations, so it
    gets its own check rather than hiding inside the similarity test.
    """
    by_slug = {f"b{c.book}c{c.chapter:02d}": c for c in parsed}
    bloated = []
    for entry in manifest["chapters"]:
        source_words = entry["words"]
        parsed_words = len(by_slug[entry["slug"]].text.split())
        if source_words and parsed_words > source_words * 1.5:
            bloated.append((entry["slug"], source_words, parsed_words))
    assert not bloated, (
        "these chapters came out far longer than their source, which means a "
        f"chapter heading was missed and two chapters merged: {bloated}"
    )


def test_text_matches_the_verified_source(parsed, manifest):
    """Every chapter's words survive the trip, near-verbatim.

    0.99 rather than 1.00 because the typesetter is allowed to normalize
    whitespace and quote characters. Anything below that means real text was
    lost or corrupted.
    """
    by_slug = {f"b{c.book}c{c.chapter:02d}": c for c in parsed}
    failures = []

    for entry in manifest["chapters"]:
        slug = entry["slug"]
        original = normalize((SOURCE / f"{slug}.txt").read_text(encoding="utf-8"))
        roundtripped = normalize(by_slug[slug].text)
        ratio = difflib.SequenceMatcher(None, original, roundtripped).ratio()
        if ratio < 0.99:
            failures.append(
                f"  {slug}: similarity {ratio:.4f} "
                f"({len(original)} words in, {len(roundtripped)} out)"
            )

    assert not failures, "chapters changed on the way through the PDF:\n" + "\n".join(failures)


def test_long_titles_do_not_leak_into_the_body(parsed, manifest):
    """A wrapped chapter title must be read as a title, all of it.

    Regression test. The first parser took "the line after the heading" as the
    title, so the six chapters whose titles wrap to a second line had their
    overflow land in the body -- retrievable, and quotable as though Epictetus
    had said it. Comparing the parsed title to the manifest catches both halves
    of that bug: a truncated title and a contaminated body.
    """
    by_slug = {f"b{c.book}c{c.chapter:02d}": c for c in parsed}
    mismatched = []
    for entry in manifest["chapters"]:
        expected = " ".join(entry["title"].split())
        actual = " ".join(by_slug[entry["slug"]].title.split())
        if expected != actual:
            mismatched.append(f"  {entry['slug']}: expected {expected!r}, parsed {actual!r}")
    assert not mismatched, "chapter titles did not survive parsing:\n" + "\n".join(mismatched)


def test_page_numbers_are_recorded(parsed):
    """Chunks carry a page number in their metadata, so parsing has to supply one."""
    assert all(c.start_page >= 1 for c in parsed), "every chapter needs a start page"
    pages = [c.start_page for c in parsed]
    assert pages == sorted(pages), "start pages should increase through the book"
