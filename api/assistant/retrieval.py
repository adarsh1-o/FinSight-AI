"""Reusable Markdown indexing and nearest-neighbor retrieval services."""

from __future__ import annotations

import os
import hashlib
import json
from pathlib import Path
from typing import Any

from .embeddings import LocalTextEmbedder
from .ingestion import DEFAULT_DOCUMENTS, chunk_documents, chunking_settings, load_markdown_documents
from .vector_store import SQLiteVectorStore


def build_index(
    paths: tuple[Path, ...] | list[Path] | None = None,
    store: SQLiteVectorStore | None = None,
    embedder: LocalTextEmbedder | None = None,
) -> dict[str, int]:
    """Rebuild the local index from approved Markdown sources."""
    documents = load_markdown_documents(DEFAULT_DOCUMENTS if paths is None else paths)
    chunks = chunk_documents(documents)
    active_store = store or SQLiteVectorStore()
    active_embedder = embedder or LocalTextEmbedder()
    vectors = active_embedder.embed([chunk.text for chunk in chunks])
    count = active_store.replace_all(
        [chunk.as_dict() for chunk in chunks], vectors,
        fingerprint=_index_fingerprint(documents, active_embedder),
    )
    return {"documents": len(documents), "chunks": count}


def _index_fingerprint(documents, embedder: LocalTextEmbedder) -> str:
    size, overlap = chunking_settings()
    state = {
        "sources": {document.path: hashlib.sha256(document.text.encode("utf-8")).hexdigest() for document in documents},
        "chunk_size": size,
        "chunk_overlap": overlap,
        "embedding_dimensions": embedder.dimensions,
        "embedding_type": "sklearn_hashing_word_bigram_v1",
    }
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class DocumentationRetriever:
    def __init__(
        self,
        store: SQLiteVectorStore | None = None,
        embedder: LocalTextEmbedder | None = None,
        top_k: int | None = None,
        auto_index: bool = True,
        paths: tuple[Path, ...] | list[Path] | None = None,
    ):
        self.store = store or SQLiteVectorStore()
        self.embedder = embedder or LocalTextEmbedder()
        self.top_k = top_k if top_k is not None else int(os.getenv("FINSIGHT_RAG_TOP_K", "4"))
        if self.top_k < 1:
            raise ValueError("FINSIGHT_RAG_TOP_K must be at least 1.")
        self.auto_index = auto_index
        self.paths = paths

    def retrieve(self, question: str) -> list[dict[str, Any]]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Enter a non-empty documentation question.")
        documents = load_markdown_documents(self.paths)
        fingerprint = _index_fingerprint(documents, self.embedder)
        if self.auto_index and not self.store.is_current(fingerprint, self.embedder.dimensions):
            build_index(paths=self.paths, store=self.store, embedder=self.embedder)
        if self.store.count() == 0:
            return []
        vector = self.embedder.embed_one(question)
        return self.store.search(vector, self.top_k)
