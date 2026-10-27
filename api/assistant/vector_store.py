"""Persistent SQLite storage for document chunks and their sparse vectors."""

from __future__ import annotations

import io
import os
import sqlite3
import zlib
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix

from .ingestion import PROJECT_ROOT


DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "processed" / "finsight_documents.sqlite3"


def configured_db_path() -> Path:
    raw_path = os.getenv("FINSIGHT_RAG_DB_PATH")
    path = Path(raw_path).expanduser() if raw_path else DEFAULT_DB_PATH
    return path if path.is_absolute() else PROJECT_ROOT / path


def _pack_vector(vector: csr_matrix) -> bytes:
    row = vector.tocsr()
    stream = io.BytesIO()
    np.savez_compressed(stream, indices=row.indices.astype(np.int32), values=row.data.astype(np.float32), dimensions=np.array([row.shape[1]], dtype=np.int32))
    return zlib.compress(stream.getvalue())


def _unpack_vector(blob: bytes) -> csr_matrix:
    with np.load(io.BytesIO(zlib.decompress(blob)), allow_pickle=False) as values:
        indices = values["indices"].astype(np.int32)
        data = values["values"].astype(np.float32)
        dimensions = int(values["dimensions"][0])
    return csr_matrix((data, indices, np.array([0, len(indices)], dtype=np.int32)), shape=(1, dimensions))


class SQLiteVectorStore:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path is not None else configured_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=20)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    section TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding BLOB NOT NULL
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_document_chunks_source ON document_chunks(source)")
            connection.execute("CREATE TABLE IF NOT EXISTS index_state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

    def replace_all(self, chunks: list[dict[str, Any]], embeddings: list[csr_matrix], fingerprint: str = "") -> int:
        """Atomically replace the index, removing stale and missing-source chunks."""
        if len(chunks) != len(embeddings):
            raise ValueError("Each document chunk must have exactly one embedding.")
        rows = []
        for chunk, vector in zip(chunks, embeddings):
            if vector.shape[0] != 1 or vector.nnz == 0 or not np.isfinite(vector.data).all():
                raise ValueError("Invalid document embedding; refusing to write an incomplete index.")
            rows.append((
                chunk["chunk_id"], chunk["document_id"], chunk["source"], chunk["section"],
                int(chunk["chunk_index"]), chunk["text"], sqlite3.Binary(_pack_vector(vector)),
            ))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM document_chunks")
            connection.executemany("""
                INSERT INTO document_chunks
                    (chunk_id, document_id, source, section, chunk_index, text, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, rows)
            connection.execute(
                "INSERT INTO index_state(key, value) VALUES('fingerprint', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (fingerprint,),
            )
            if embeddings:
                connection.execute(
                    "INSERT INTO index_state(key, value) VALUES('dimensions', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(embeddings[0].shape[1]),),
                )
            else:
                connection.execute("DELETE FROM index_state WHERE key='dimensions'")
        return len(rows)

    def is_current(self, fingerprint: str, dimensions: int) -> bool:
        with self._connect() as connection:
            state = {row["key"]: row["value"] for row in connection.execute("SELECT key, value FROM index_state")}
            chunk_count = int(connection.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0])
        dimensions_match = state.get("dimensions") == str(dimensions) if chunk_count else "dimensions" not in state
        return state.get("fingerprint") == fingerprint and dimensions_match

    def count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0])

    def search(self, query: csr_matrix, top_k: int = 4) -> list[dict[str, Any]]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1.")
        if query.shape[0] != 1 or query.nnz == 0 or not np.isfinite(query.data).all():
            raise ValueError("Search query embedding is empty or invalid.")
        scored = []
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM document_chunks").fetchall()
        for row in rows:
            stored = _unpack_vector(row["embedding"])
            if stored.shape[1] != query.shape[1]:
                continue
            score = float(query.multiply(stored).sum())
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], item[1]["source"], item[1]["chunk_index"]))
        return [
            {
                "chunk_id": row["chunk_id"], "document_id": row["document_id"],
                "source": row["source"], "section": row["section"],
                "chunk_index": row["chunk_index"], "text": row["text"], "score": score,
            }
            for score, row in scored[:top_k]
        ]
