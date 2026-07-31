"""Turn parsed chapters into retrievable chunks.

Input:  the ParsedChapter list from parse_pdf.py
Output: LlamaIndex TextNodes, each carrying the book, chapter, page and its
        position within the chapter

The numbers, and why (plan section 3):

  ~400 tokens per chunk. A median chapter is about 1,500 tokens, so a chapter
  becomes three or four chunks. Small enough that a chunk is about one thing;
  large enough to carry a whole argument, which matters because Epictetus makes
  his point over several sentences rather than in one line.

  ~60 tokens of overlap. A thought that straddles a boundary stays findable
  from either side.

  Chapter boundaries are hard walls. Each chapter is split on its own, so no
  chunk can ever span two chapters. This is not a tidiness preference: a chunk
  spanning the end of Book 2 Chapter 5 and the start of Chapter 6 would be
  filed under one chapter and quoted as evidence for the other, and "a specific
  fact in a specific chapter" is exactly what the agent is graded on.

Counting is done with the tokenizer of the embedding model that will actually
see these chunks, so "400 tokens" means 400 of the tokens that matter, not 400
of some other model's.
"""

from __future__ import annotations

import logging
from collections import Counter

import tiktoken
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document, TextNode

from agent.retrieval.parse_pdf import ParsedChapter

log = logging.getLogger("retrieval.chunking")

CHUNK_SIZE_TOKENS = 400
CHUNK_OVERLAP_TOKENS = 60

# text-embedding-3-small uses the cl100k_base tokenizer.
_TOKENIZER = tiktoken.get_encoding("cl100k_base")


def _splitter() -> SentenceSplitter:
    return SentenceSplitter(
        chunk_size=CHUNK_SIZE_TOKENS,
        chunk_overlap=CHUNK_OVERLAP_TOKENS,
        tokenizer=_TOKENIZER.encode,
    )


def chapters_to_nodes(chapters: list[ParsedChapter]) -> list[TextNode]:
    splitter = _splitter()
    nodes: list[TextNode] = []

    for chapter in chapters:
        document = Document(
            text=chapter.text,
            metadata={
                "book": chapter.book,
                "chapter": chapter.chapter,
                "title": chapter.title,
                "citation": chapter.citation,
                "page": chapter.start_page,
                "slug": chapter.slug,
            },
        )
        # One splitter call per chapter is what makes the chapter wall real.
        chapter_nodes = splitter.get_nodes_from_documents([document])

        for position, node in enumerate(chapter_nodes):
            node.metadata["chunk_ix"] = position
            node.metadata["chunks_in_chapter"] = len(chapter_nodes)

            # The chapter title is topical and worth embedding. The book and
            # chapter numbers are bookkeeping -- embedding them would let a
            # question that merely mentions a number drift toward the wrong
            # passage, and they are never what makes a passage relevant.
            node.excluded_embed_metadata_keys = [
                "book",
                "chapter",
                "citation",
                "page",
                "slug",
                "chunk_ix",
                "chunks_in_chapter",
            ]
            # The LLM is given the citation separately, in a controlled format.
            # Leaving raw metadata in the prompt text invites it to read the
            # numbers aloud, and Epictetus does not cite himself.
            node.excluded_llm_metadata_keys = list(node.metadata.keys())

        nodes.extend(chapter_nodes)

    _log_shape(nodes, chapters)
    return nodes


def _log_shape(nodes: list[TextNode], chapters: list[ParsedChapter]) -> None:
    per_chapter = Counter(f"b{n.metadata['book']}c{n.metadata['chapter']:02d}" for n in nodes)
    lengths = sorted(len(_TOKENIZER.encode(n.text)) for n in nodes)
    if not lengths:
        log.error("[retrieval.chunking] produced no chunks at all")
        return

    biggest = per_chapter.most_common(3)
    log.info(
        "[retrieval.chunking] %d chunks from %d chapters | tokens min %d / median %d / max %d",
        len(nodes),
        len(chapters),
        lengths[0],
        lengths[len(lengths) // 2],
        lengths[-1],
    )
    # Plan section 10 flags the three very long chapters as a risk: one chapter
    # producing a lot of chunks can crowd the retrieved pool. Log it so the
    # eval harness has something to check against.
    log.info("[retrieval.chunking] chapters producing the most chunks: %s", biggest)
