"""Typeset the verified Wikisource text into corpus/discourses.pdf.

Build-time only, and the reason the whole corpus story hangs together.

The brief asks for RAG over a PDF. The two ways to get a Discourses PDF were a
scanned copy from archive.org -- whose OCR is bad enough that roughly a third of
its words carry low confidence -- or building a clean one from text that can be
checked word for word against Wikisource. This script is the second option.
The trade is written up in the README: we give up "found in the wild" and get a
corpus where every word is verifiable.

Input:  corpus/source/*.txt plus manifest.json (from fetch_wikisource.py)
Output: corpus/discourses.pdf -- a real book with a title page, four book
        openers, and 95 chapters

Steps:
  1. Read the manifest so chapters are laid out in reading order.
  2. Emit a title page and, at the start of each book, a book opener page.
  3. For each chapter emit a machine-readable heading line, then the chapter
     title, then the body paragraphs.
  4. Draw a running header and a page-number footer on every page.

The heading line is written as "BOOK 1, CHAPTER 5" -- upper case, that exact
punctuation. It reads fine to a human and gives agent/retrieval/parse_pdf.py an
unambiguous marker that cannot collide with the translated prose. Chapters run
on within a page (only books start a new page), because that is what a real book
does and it is the harder case for the parser to get right.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from fontTools.ttLib import TTFont as TTFont_reader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer

CORPUS = Path(__file__).resolve().parents[1]
SOURCE = CORPUS / "source"
OUT_PDF = CORPUS / "discourses.pdf"
FONT_DIR = Path(__file__).resolve().parent / "fonts"

RUNNING_HEADER = "The Discourses of Epictetus"
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV"}

log = logging.getLogger("corpus.typeset")


def register_fonts() -> None:
    """Use DejaVu Serif, which covers the Greek that Long leaves untranslated.

    The obvious choice was a built-in font like Times-Roman, but those are
    Latin-1 only. Long's translation quotes Greek inline in dozens of chapters,
    including polytonic forms, and a Latin-1 font would drop every one of those
    characters silently -- the corpus would look fine and be quietly wrong.

    The font files are committed rather than taken from the host, so the PDF
    builds the same way inside the worker image as it does on a laptop.
    """
    pdfmetrics.registerFont(TTFont("Serif", str(FONT_DIR / "DejaVuSerif.ttf")))
    pdfmetrics.registerFont(TTFont("Serif-Bold", str(FONT_DIR / "DejaVuSerif-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Serif-Italic", str(FONT_DIR / "DejaVuSerif-Italic.ttf")))
    pdfmetrics.registerFontFamily(
        "Serif", normal="Serif", bold="Serif-Bold", italic="Serif-Italic"
    )


BODY = ParagraphStyle(
    "Body",
    fontName="Serif",
    fontSize=11,
    leading=15.5,
    alignment=TA_JUSTIFY,
    firstLineIndent=18,
    spaceAfter=2,
)
CHAPTER_HEADING = ParagraphStyle(
    "ChapterHeading",
    fontName="Serif-Bold",
    fontSize=10,
    leading=13,
    spaceBefore=22,
    spaceAfter=3,
    textColor="#333333",
)
CHAPTER_TITLE = ParagraphStyle(
    "ChapterTitle",
    fontName="Serif-Italic",
    fontSize=12.5,
    leading=16,
    spaceAfter=10,
)
BOOK_TITLE = ParagraphStyle(
    "BookTitle", fontName="Serif-Bold", fontSize=26, leading=32, alignment=TA_CENTER
)
TITLE_MAIN = ParagraphStyle(
    "TitleMain", fontName="Serif-Bold", fontSize=30, leading=36, alignment=TA_CENTER
)
TITLE_SUB = ParagraphStyle(
    "TitleSub", fontName="Serif", fontSize=13, leading=19, alignment=TA_CENTER
)


def draw_furniture(canvas, doc) -> None:
    """Running header and page-number footer.

    parse_pdf.py strips both by content. The footer is written as "- 12 -" so it
    cannot be confused with a line of prose that happens to be a bare number.
    """
    canvas.saveState()
    canvas.setFont("Serif-Italic", 8)
    canvas.setFillColor("#666666")
    canvas.drawCentredString(LETTER[0] / 2, LETTER[1] - 0.62 * inch, RUNNING_HEADER)
    canvas.setFont("Serif", 8.5)
    canvas.drawCentredString(LETTER[0] / 2, 0.55 * inch, f"- {doc.page} -")
    canvas.restoreState()


def check_font_covers_corpus(chapters: list[dict]) -> None:
    """Fail the build if the font cannot draw something in the source text.

    A missing glyph does not raise -- it draws a blank or a box, and the word
    quietly disappears from the extracted text too. That is the worst kind of
    corpus bug, because everything downstream still looks healthy. So the
    coverage question gets asked here, up front, against the real font file.
    """
    covered: set[int] = set()
    font = TTFont_reader(FONT_DIR / "DejaVuSerif.ttf")
    for table in font["cmap"].tables:
        covered |= set(table.cmap.keys())

    missing: dict[str, str] = {}
    for entry in chapters:
        text = (SOURCE / f"{entry['slug']}.txt").read_text(encoding="utf-8")
        for character in set(text):
            if character in "\n\r\t" or character in missing:
                continue
            if ord(character) not in covered:
                missing[character] = entry["slug"]

    if missing:
        detail = ", ".join(f"{c!r} (U+{ord(c):04X}, first in {s})" for c, s in missing.items())
        raise ValueError(
            f"the PDF font cannot render these characters from the source text: {detail}"
        )
    log.info("[corpus.typeset] font covers every character in the corpus")


def build_story(manifest: dict) -> list:
    story: list = [
        Spacer(1, 2.2 * inch),
        Paragraph("The Discourses", TITLE_MAIN),
        Paragraph("of Epictetus", TITLE_MAIN),
        Spacer(1, 0.5 * inch),
        Paragraph("as reported by Arrian", TITLE_SUB),
        Spacer(1, 0.3 * inch),
        Paragraph("Translated by George Long", TITLE_SUB),
        Spacer(1, 1.4 * inch),
        Paragraph(
            "Text from Wikisource, the 1877 George Long translation. "
            "Typeset for the Epictetus voice agent; every word is verifiable "
            "against the source.",
            TITLE_SUB,
        ),
        PageBreak(),
    ]

    current_book: int | None = None
    for entry in manifest["chapters"]:
        if entry["book"] != current_book:
            current_book = entry["book"]
            story += [
                Spacer(1, 3.0 * inch),
                Paragraph(f"BOOK {ROMAN[current_book]}", BOOK_TITLE),
                PageBreak(),
            ]

        story.append(
            Paragraph(f"BOOK {entry['book']}, CHAPTER {entry['chapter']}", CHAPTER_HEADING)
        )
        story.append(Paragraph(escape(entry["title"] or "Untitled"), CHAPTER_TITLE))

        text = (SOURCE / f"{entry['slug']}.txt").read_text(encoding="utf-8")
        for paragraph in text.split("\n\n"):
            paragraph = " ".join(paragraph.split())
            if paragraph:
                story.append(Paragraph(escape(paragraph), BODY))

    return story


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    manifest_path = SOURCE / "manifest.json"
    if not manifest_path.exists():
        log.error("[corpus.typeset] %s missing. Run fetch_wikisource.py first.", manifest_path)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chapters = manifest["chapters"]
    log.info("[corpus.typeset] typesetting %d chapters", len(chapters))

    register_fonts()
    check_font_covers_corpus(chapters)

    doc = BaseDocTemplate(
        str(OUT_PDF),
        pagesize=LETTER,
        title="The Discourses of Epictetus",
        author="Epictetus, translated by George Long",
        subject="Stoic philosophy",
        leftMargin=1.05 * inch,
        rightMargin=1.05 * inch,
        topMargin=0.95 * inch,
        bottomMargin=0.85 * inch,
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body", showBoundary=0
    )
    doc.addPageTemplates(
        [PageTemplate(id="main", frames=[frame], onPage=draw_furniture)]
    )
    doc.build(build_story(manifest))

    size_mb = OUT_PDF.stat().st_size / 1_000_000
    log.info("[corpus.typeset] wrote %s (%.1f MB)", OUT_PDF, size_mb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
