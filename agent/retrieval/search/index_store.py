"""Build and load the on-disk index.

Input (build):  corpus/discourses.pdf
Output (build): index/ -- LlamaIndex's persisted docstore, index store and
                vector store, committed to the repository

Steps (build): parse the PDF -> chunk it -> embed the chunks -> persist.

Why a plain file-backed store and not a vector database (plan section 3): the
corpus is about 500 chunks and never changes. A database would add a network
hop to every turn of a voice call, a service to keep alive, and a bill, in
exchange for nothing at this size. The index files are small enough to commit,
so the brief's "vector store" deliverable is a thing you can read in the repo
rather than a blob inside an image. It loads into memory when the worker starts.

The BM25 side is rebuilt from the same persisted docstore at load time rather
than persisted separately. Over 500 chunks that takes a moment, and it means
there is one copy of the corpus on disk, not two that can drift apart.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from llama_index.core import StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.schema import TextNode
from llama_index.embeddings.openai import OpenAIEmbedding

log = logging.getLogger("retrieval.index")

REPO = Path(__file__).resolve().parents[3]
INDEX_DIR = REPO / "index"
CORPUS_PDF = REPO / "corpus" / "discourses.pdf"

EMBED_MODEL = "text-embedding-3-small"


def embedding_model() -> OpenAIEmbedding:
    """The one place the embedding model is named.

    Costs money. Roughly a cent to embed the whole corpus once, and a fraction
    of a cent per call thereafter, but it does need OPENAI_API_KEY.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Embedding the corpus and embedding each "
            "question both need it. See .env.example."
        )
    return OpenAIEmbedding(model=EMBED_MODEL)


def build_index(index_dir: Path = INDEX_DIR, pdf_path: Path = CORPUS_PDF) -> list[TextNode]:
    """Parse the PDF, chunk it, embed it, write it to disk. Run once."""
    from agent.retrieval.chunking import chapters_to_nodes
    from agent.retrieval.parse_pdf import parse_discourses_pdf

    chapters = parse_discourses_pdf(pdf_path)
    nodes = chapters_to_nodes(chapters)

    log.info("[retrieval.index] embedding %d chunks with %s", len(nodes), EMBED_MODEL)
    index = VectorStoreIndex(nodes, embed_model=embedding_model(), show_progress=True)

    index_dir.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(index_dir))

    written = sum(f.stat().st_size for f in index_dir.glob("*.json"))
    log.info(
        "[retrieval.index] persisted %d chunks to %s (%.1f MB)",
        len(nodes),
        index_dir,
        written / 1_000_000,
    )
    return nodes


def load_index(index_dir: Path = INDEX_DIR) -> VectorStoreIndex:
    """Load the committed index into memory. Called once when the worker starts."""
    if not (index_dir / "docstore.json").exists():
        raise FileNotFoundError(
            f"no index at {index_dir}. Build it with:\n"
            f"  python -m agent.retrieval.search.index_store"
        )
    storage_context = StorageContext.from_defaults(persist_dir=str(index_dir))
    index = load_index_from_storage(storage_context, embed_model=embedding_model())
    log.info(
        "[retrieval.index] loaded %d chunks from %s",
        len(storage_context.docstore.docs),
        index_dir,
    )
    return index


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    build_index()
