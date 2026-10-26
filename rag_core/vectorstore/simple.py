"""Magasin vectoriel « simple » : NumPy + SQLite, sans dépendance lourde."""

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from rag_core.models import Chunk, SearchResult
from rag_core.vectorstore.base import VectorStore, ensure_directory

_SCHEMA_CHUNKS = """
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    page INTEGER,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    metadata TEXT NOT NULL,
    embedding BLOB NOT NULL
)
"""

_SCHEMA_META = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)
"""


class SimpleVectorStore(VectorStore):
    """Index local : les vecteurs sont des BLOB float32 dans un SQLite.

    La recherche charge la matrice, normalise, puis fait un produit
    scalaire (cosinus pré-normalisé) — vectorisé avec NumPy.
    """

    def __init__(self, path: Path) -> None:
        self._dir = ensure_directory(path)
        self._conn = sqlite3.connect(self._dir / "index.sqlite3")
        with self._conn:
            self._conn.execute(_SCHEMA_CHUNKS)
            self._conn.execute(_SCHEMA_META)

    # -- Écriture ---------------------------------------------------------------

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks et embeddings doivent avoir la même taille")
        with self._conn:
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                blob = np.asarray(embedding, dtype=np.float32).tobytes()
                self._conn.execute(
                    """
                    INSERT INTO chunks (id, source, page, chunk_index, text, metadata, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        source = excluded.source,
                        page = excluded.page,
                        chunk_index = excluded.chunk_index,
                        text = excluded.text,
                        metadata = excluded.metadata,
                        embedding = excluded.embedding
                    """,
                    (
                        chunk.id,
                        chunk.source,
                        chunk.page,
                        chunk.index,
                        chunk.text,
                        json.dumps(chunk.metadata, ensure_ascii=False),
                        blob,
                    ),
                )

    def delete_by_source(self, source: str) -> int:
        with self._conn:
            cursor = self._conn.execute("DELETE FROM chunks WHERE source = ?", (source,))
        return cursor.rowcount

    def clear(self) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM chunks")
            self._conn.execute("DELETE FROM meta")

    # -- Recherche ----------------------------------------------------------------

    def search(self, query_embedding: list[float], top_k: int) -> list[SearchResult]:
        rows = self._conn.execute(
            "SELECT id, source, page, chunk_index, text, metadata, embedding FROM chunks"
        ).fetchall()
        if not rows or top_k <= 0:
            return []
        matrix = np.frombuffer(
            b"".join(row[6] for row in rows), dtype=np.float32
        ).reshape(len(rows), -1)
        query = np.asarray(query_embedding, dtype=np.float32)

        # Cosinus : produit scalaire des vecteurs normalisés.
        norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(query)
        scores = np.zeros(len(rows), dtype=np.float32)
        mask = norms > 0
        scores[mask] = (matrix[mask] @ query) / norms[mask]

        k = min(top_k, len(rows))
        # argpartition sélectionne les k meilleurs en O(n), puis on trie.
        top = np.argpartition(-scores, k - 1)[:k]
        top = top[np.argsort(-scores[top], kind="stable")]
        return [
            SearchResult(chunk=self._row_to_chunk(rows[i]), score=float(scores[i])) for i in top
        ]

    # -- Lecture ----------------------------------------------------------------------

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])

    def list_sources(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT source FROM chunks ORDER BY source"
        ).fetchall()
        return [row[0] for row in rows]

    def get_source_hash(self, source: str) -> str | None:
        row = self._conn.execute(
            "SELECT metadata FROM chunks WHERE source = ? LIMIT 1", (source,)
        ).fetchone()
        if row is None:
            return None
        metadata = json.loads(row[0])
        return metadata.get("file_hash")

    def iter_chunks(self) -> Iterator[Chunk]:
        cursor = self._conn.execute(
            "SELECT id, source, page, chunk_index, text, metadata FROM chunks ORDER BY source, "
            "chunk_index"
        )
        for row in cursor:
            yield self._row_to_chunk(row)

    def get_embedding_model(self) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key = 'embedding_model'"
        ).fetchone()
        return row[0] if row else None

    def set_embedding_model(self, name: str) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO meta (key, value) VALUES ('embedding_model', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (name,),
            )

    # -- Internes -------------------------------------------------------------------------

    def close(self) -> None:
        """Ferme la connexion SQLite (propre en fin de processus/tests)."""
        self._conn.close()

    @staticmethod
    def _row_to_chunk(row: tuple) -> Chunk:
        return Chunk(
            id=row[0],
            source=row[1],
            page=row[2],
            index=row[3],
            text=row[4],
            metadata=json.loads(row[5]),
        )
