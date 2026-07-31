"""Fetch the Discourses of Epictetus (George Long translation) from Wikisource.

Build-time only. Nothing at runtime reads these files -- the runtime pipeline
parses the generated PDF instead (see corpus/build/typeset_pdf.py and
agent/retrieval/parse_pdf.py).

Input:  nothing (hits the Wikisource API)
Output: corpus/source/b<book>c<chapter>.txt, one file per chapter, plus
        corpus/source/manifest.json listing every chapter with its title and
        word count.

Steps:
  1. Ask the Wikisource API for every subpage of the Long translation.
  2. Keep the ones matching "/Book N/Chapter M".
  3. Read the work's table of contents once to get all 95 chapter titles. The
     chapter pages themselves do not carry their title, only "Book N, Chapter M".
  4. Render each chapter to HTML (the pages transclude proofread scans, so the
     plain wikitext is nearly empty -- we need the rendered form).
  5. Strip navigation, footnotes, page-number markers and reference links,
     leaving the translated body text.
  6. Write one file per chapter and a manifest.

Safe to re-run: chapters already on disk are skipped, so a run interrupted by
Wikisource rate limiting picks up where it left off.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

API = "https://en.wikisource.org/w/api.php"
WORK = "The Discourses of Epictetus; with the Encheiridion and Fragments"
USER_AGENT = (
    "epictetus-voice-agent/1.0 (Bluejay take-home; corpus build script; "
    "contact via repository)"
)

SOURCE_DIR = Path(__file__).resolve().parents[1] / "source"

log = logging.getLogger("corpus.fetch")

# Rendered-page furniture that is not part of the translation.
DROP_SELECTORS = [
    ".ws-noexport",
    ".wst-header",
    ".wst-header-mainblock",
    "style",
    "script",
    "sup.reference",
    ".mw-editsection",
    ".reflist",
    ".references",
    "#Footnotes",
    "table",
]

# Wikisource marks the boundary between two scanned pages with an anchor
# carrying this class; it renders as an invisible span but leaves stray
# artifacts if we do not remove it explicitly.
PAGE_MARKER_CLASSES = ["pagenum", "ws-pagenum", "mw-cite-backlink"]


def api_get(session: requests.Session, params: dict) -> dict:
    """One Wikisource API call.

    Wikisource rate-limits anonymous parse calls hard (HTTP 429). We back off
    for as long as it asks, and a good while even if it does not say.
    """
    params = {**params, "format": "json", "formatversion": "2"}
    last_error: Exception | None = None
    for attempt in range(6):
        try:
            response = session.get(API, params=params, timeout=45)
            if response.status_code == 429:
                wait = float(response.headers.get("Retry-After", 0) or 0)
                wait = max(wait, 10.0 * (attempt + 1))
                log.warning(
                    "[corpus.fetch] rate limited, sleeping %.0fs (attempt %d/6)",
                    wait,
                    attempt + 1,
                )
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - retry anything transient
            last_error = exc
            log.warning("[corpus.fetch] API call failed (attempt %d/6): %s", attempt + 1, exc)
            time.sleep(5.0 * (attempt + 1))
    raise RuntimeError(f"Wikisource API call failed after 6 attempts: {last_error}")


def fetch_titles(session: requests.Session) -> dict[tuple[int, int], str]:
    """(book, chapter) -> chapter title, read once from the work's contents page.

    A chapter page renders its own heading as just "Book 1, Chapter 2", so the
    real titles have to come from the table of contents. Titles are used for
    the PDF's structure and for generating eval questions; they are NOT used
    for citation, which is book + chapter only (plan section 3).
    """
    data = api_get(session, {"action": "parse", "page": WORK, "prop": "text"})
    soup = BeautifulSoup(data["parse"]["text"], "lxml")
    titles: dict[tuple[int, int], str] = {}
    for link in soup.find_all("a", href=True):
        match = re.search(r"/Book_(\d+)/Chapter_(\d+)$", link["href"])
        if not match:
            continue
        key = (int(match.group(1)), int(match.group(2)))
        text = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
        # The contents page links each chapter once by title; ignore any later
        # navigational repeat so the first (titled) link wins.
        if text and key not in titles:
            titles[key] = text
    log.info("[corpus.fetch] read %d chapter titles from the contents page", len(titles))
    return titles


def list_chapter_pages(session: requests.Session) -> list[tuple[int, int, str]]:
    """Every "/Book N/Chapter M" subpage, sorted by book then chapter."""
    data = api_get(
        session,
        {
            "action": "query",
            "list": "allpages",
            "apprefix": f"{WORK}/",
            "aplimit": "500",
        },
    )
    pages: list[tuple[int, int, str]] = []
    for page in data["query"]["allpages"]:
        match = re.search(r"/Book (\d+)/Chapter (\d+)$", page["title"])
        if match:
            pages.append((int(match.group(1)), int(match.group(2)), page["title"]))
    pages.sort()
    log.info("[corpus.fetch] found %d chapter pages", len(pages))
    return pages


def clean_html(raw_html: str) -> str:
    """Rendered chapter HTML -> the translated body text, paragraphs blank-line separated."""
    soup = BeautifulSoup(raw_html, "lxml")

    for selector in DROP_SELECTORS:
        for node in soup.select(selector):
            node.decompose()
    for class_name in PAGE_MARKER_CLASSES:
        for node in soup.find_all(class_=class_name):
            node.decompose()

    # Everything from a "Footnotes"/"Notes" heading onward is apparatus.
    for heading in soup.find_all(["h2", "h3"]):
        text = heading.get_text(strip=True).lower()
        if text in {"footnotes", "notes", "references"}:
            for sibling in list(heading.find_all_next()):
                sibling.decompose()
            heading.decompose()

    paragraphs: list[str] = []
    for node in soup.find_all("p"):
        text = node.get_text(" ", strip=True)
        text = re.sub(r"\[\d+\]", "", text)  # leftover footnote markers
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            paragraphs.append(text)

    return "\n\n".join(paragraphs)


def fetch_chapter(session: requests.Session, page_title: str) -> str:
    data = api_get(session, {"action": "parse", "page": page_title, "prop": "text"})
    return clean_html(data["parse"]["text"])


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    pages = list_chapter_pages(session)
    if not pages:
        log.error("[corpus.fetch] no chapter pages found -- has the work been renamed?")
        return 1

    titles = fetch_titles(session)

    manifest = []
    empty: list[str] = []

    for book, chapter, page_title in pages:
        slug = f"b{book}c{chapter:02d}"
        path = SOURCE_DIR / f"{slug}.txt"

        # Resume: a run killed by rate limiting can just be started again.
        if path.exists() and path.read_text(encoding="utf-8").strip():
            body = path.read_text(encoding="utf-8").strip()
            cached = True
        else:
            body = fetch_chapter(session, page_title)
            path.write_text(body + "\n", encoding="utf-8")
            cached = False

        words = len(body.split())
        if words == 0:
            empty.append(slug)
            log.error("[corpus.fetch] %s came back EMPTY (%s)", slug, page_title)

        title = titles.get((book, chapter), "")
        manifest.append(
            {
                "slug": slug,
                "book": book,
                "chapter": chapter,
                "title": title,
                "words": words,
                "source_page": page_title,
            }
        )
        log.info(
            "[corpus.fetch] %s %s %5d words  %s",
            slug,
            "cached" if cached else "  new ",
            words,
            title[:58],
        )
        if not cached:
            time.sleep(1.0)  # be polite to Wikisource; it rate-limits hard

    (SOURCE_DIR / "manifest.json").write_text(
        json.dumps(
            {
                "work": WORK,
                "translation": "George Long",
                "source": "https://en.wikisource.org/wiki/" + WORK.replace(" ", "_"),
                "chapters": manifest,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    total_words = sum(entry["words"] for entry in manifest)
    log.info(
        "[corpus.fetch] wrote %d chapters, %s words total, to %s",
        len(manifest),
        f"{total_words:,}",
        SOURCE_DIR,
    )
    if empty:
        log.error("[corpus.fetch] %d chapters are empty: %s", len(empty), empty)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
