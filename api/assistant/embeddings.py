"""Offline, fixed-dimension text embeddings built with scikit-learn."""

from __future__ import annotations

import os

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import HashingVectorizer


class EmbeddingError(ValueError):
    """Raised when valid embeddings cannot be produced."""


class LocalTextEmbedder:
    """Create normalized hashed word and bigram vectors without a network service.

    These vectors are lightweight lexical embeddings, not transformer semantics.
    The fixed feature count lets indexing and query encoding always match.
    """

    def __init__(self, dimensions: int | None = None):
        self.dimensions = dimensions or int(os.getenv("FINSIGHT_RAG_EMBEDDING_DIMENSIONS", "16384"))
        if self.dimensions < 256:
            raise ValueError("Embedding dimensions must be at least 256.")
        self._vectorizer = HashingVectorizer(
            n_features=self.dimensions,
            alternate_sign=False,
            norm="l2",
            ngram_range=(1, 2),
            strip_accents="unicode",
        )

    def embed(self, texts: list[str]) -> list[csr_matrix]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise EmbeddingError("Cannot embed empty or non-text input.")
        try:
            matrix = self._vectorizer.transform(texts).tocsr().astype(np.float32)
        except (TypeError, ValueError) as error:
            raise EmbeddingError("Local text embedding failed.") from error
        results = []
        for row_index in range(matrix.shape[0]):
            row = matrix.getrow(row_index)
            if row.nnz == 0 or not np.isfinite(row.data).all():
                raise EmbeddingError("Text produced an empty or invalid embedding.")
            results.append(row)
        return results

    def embed_one(self, text: str) -> csr_matrix:
        return self.embed([text])[0]
