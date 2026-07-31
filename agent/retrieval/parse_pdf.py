"""Read the Discourses PDF back out into labelled chapters.

This is the runtime entry point for the corpus. Nothing downstream reads the
Wikisource .txt files -- those exist only to build the PDF. Everything the agent
ever cites comes through this function, using a plain PDF reader on a plain PDF.

Input:  a path to the typeset Discourses PDF
Output: a list of ParsedChapter -- book, chapter, title, body text, start page,
        in reading order

Steps:
  1. Pull out every run of text with the size it was drawn at, page by page.
  2. Work out the body text size: the size most of the document is set in.
  3. Drop anything smaller than that -- running heads and page numbers.
  4. Split on the chapter heading line ("BOOK 1, CHAPTER 5").
  5. Take the larger-than-body lines right after a heading as the chapter title,
     however many lines it runs to, and the body-size lines as the text.

Two decisions worth stating.

Chapters are found by a regex over the text, not by the PDF's bookmarks. An
arbitrary PDF would not have bookmarks, and using them would make this a
different code path from the one a real document takes.

Titles are found by text size, not by counting lines. The first version of this
parser took "the line after the heading" as the title, which quietly broke on
the six chapters whose titles are long enough to wrap: the overflow landed in
the body, where it could be retrieved and quoted as though Epictetus had said
it. Size is how heading detection actually works in PDF parsing, and it does not
care how long a title is.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

log = logging.getLogger("retrieval.parse_pdf")

# What the typesetter writes above every chapter. Upper case with this exact
# punctuation never occurs in the translated prose, so it cannot fire on body
# text by accident.
HEADING = re.compile(r"^BOOK\s+(\d+),\s+CHAPTER\s+(\d+)$")

# Text sizes vary by a hair between runs; anything within this of the body size
# counts as body text.
SIZE_TOLERANCE = 0.6


@dataclass(frozen=True)
class ParsedChapter:
    book: int
    chapter: int
    title: str
    text: str
    start_page: int

    @property
    def slug(self) -> str:
        return f"b{self.book}c{self.chapter:02d}"

    @property
    def citation(self) -> str:
        """What the source panel shows. Book and chapter only -- no title.

        Plan section 3: Epictetus speaks, the panel cites.
        """
        return f"Book {self.book}, Chapter {self.chapter}"


@dataclass(frozen=True)
class _Line:
    page: int
    size: float
    text: str


def _read_lines(pdf_path: Path) -> list[_Line]:
    """Every line of the document, with the text size it was drawn at."""
    reader = PdfReader(str(pdf_path))
    lines: list[_Line] = []

    for page_number, page in enumerate(reader.pages, start=1):
        collected: list[tuple[float, str]] = []

        def visitor(text, cm, tm, font_dict, font_size, _sink=collected):
            if text and text.strip():
                _sink.append((float(font_size or 0.0), text))

        page.extract_text(visitor_text=visitor)

        for size, text in collected:
            for piece in text.splitlines():
                piece = piece.strip()
                if piece:
                    lines.append(_Line(page=page_number, size=size, text=piece))

    log.info(
        "[retrieval.parse_pdf] read %d lines from %d pages of %s",
        len(lines),
        len(reader.pages),
        pdf_path.name,
    )
    return lines


def _body_size(lines: list[_Line]) -> float:
    """The size most of the document's characters are set in.

    Weighted by how much text is at each size, not by how many lines, so a
    hundred short headings cannot outvote the actual prose.
    """
    weights: Counter[float] = Counter()
    for line in lines:
        weights[round(line.size, 1)] += len(line.text)
    size, _ = weights.most_common(1)[0]
    log.info("[retrieval.parse_pdf] body text size looks like %.1f", size)
    return size


def parse_discourses_pdf(pdf_path: Path | str) -> list[ParsedChapter]:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"corpus PDF not found: {pdf_path}")

    lines = _read_lines(pdf_path)
    if not lines:
        raise ValueError(f"no text came out of {pdf_path} -- is it a scan rather than text?")

    body_size = _body_size(lines)

    chapters: list[ParsedChapter] = []
    current: dict | None = None
    body: list[str] = []
    title_parts: list[str] = []
    in_title = False

    def close_current() -> None:
        if current is None:
            return
        chapters.append(
            ParsedChapter(
                book=current["book"],
                chapter=current["chapter"],
                title=" ".join(title_parts).strip(),
                text=" ".join(body).strip(),
                start_page=current["page"],
            )
        )

    for line in lines:
        heading = HEADING.match(line.text)
        if heading:
            close_current()
            current = {
                "book": int(heading.group(1)),
                "chapter": int(heading.group(2)),
                "page": line.page,
            }
            body = []
            title_parts = []
            in_title = True
            continue

        if current is None:
            continue  # front matter, before the first chapter

        is_body_size = abs(line.size - body_size) <= SIZE_TOLERANCE
        is_larger = line.size - body_size > SIZE_TOLERANCE

        if in_title:
            if is_larger:
                # Still in the title, however many lines it wraps to.
                title_parts.append(line.text)
                continue
            if not is_body_size:
                # Smaller than body: a running head or page number, picked up
                # because this chapter's heading landed at the foot of a page
                # and the title continues on the next one. Skip it and stay in
                # the title.
                continue
            in_title = False

        if not is_body_size:
            # Running head, page number, or a book opener between chapters.
            continue

        body.append(line.text)

    close_current()

    log.info("[retrieval.parse_pdf] parsed %d chapters", len(chapters))
    if not chapters:
        raise ValueError(
            f"no chapter headings found in {pdf_path}. Expected lines like "
            f"'BOOK 1, CHAPTER 5' -- was this PDF built by corpus/build/typeset_pdf.py?"
        )
    return chapters
