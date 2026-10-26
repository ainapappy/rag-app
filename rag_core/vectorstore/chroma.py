"""Magasin vectoriel Chroma (optionnel : nécessite requirements-chroma.txt)."""

import json
from collections.abc import Iterator
from pathlib import Path

from rag_core.exceptions import VectorStoreError
from rag_core.models import Chunk, SearchResult
from rag_core.vectorstore.base import VectorStore, ensure_directory

# Chroma n'accepte pas NULL dans ses métadonnées : page=None est stockée en -1.
_PAGE_NULL = -1
_ITER_PAGE_SIZE = 100


class ChromaVectorStore(VectorStore):
    """Index persistant via chromadb (collection en distance cosinus).

    Import paresseux de `chromadb` dans le constructeur : le projet
    fonctionne sans ce paquet tant qu'on utilise l'index « simple ».
    """

    def __init__(self, path: Path, collection_name: str = "rag") -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise VectorStoreError(
                "chromadb n'est pas installé : lancez "
                "`pip install -r requirements-chroma.txt` ou utilisez VECTOR_STORE=simple."
            ) from exc
        self._path = ensure_directory(path)
        self._collection_name = collection_name
        self._client = chromadb.PersistentClient(path=str(self._path))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    # -- Écriture ---------------------------------------------------------------

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks et embeddings doivent avoir la même taille")
        if not chunks:
            return
        self._collection.add(
            ids=[chunk.id for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=[self._to_chroma_metadata(chunk) for chunk in chunks],
        )

    def delete_by_source(self, source: str) -> int:
        found = self._collection.get(where={"source": source}, include=[])
        count = len(found["ids"])
        if count:
            self._collection.delete(where={"source": source})
        return count

    def clear(self) -> None:
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    # -- Recherche ----------------------------------------------------------------

    def search(self, query_embedding: list[float], top_k: int) -> list[SearchResult]:
        if top_k <= 0 or self._collection.count() == 0:
            return []
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        results: list[SearchResult] = []
        for chunk_id, distance, document, metadata in zip(
            result["ids"][0],
            result["distances"][0],
            result["documents"][0],
            result["metadatas"][0],
            strict=True,
        ):
            # Chroma renvoie une distance cosinus : similarité = 1 - distance.
            results.append(
                SearchResult(
                    chunk=self._from_chroma(chunk_id, document, metadata),
                    score=1.0 - float(distance),
                )
            )
        return sorted(results, key=lambda r: r.score, reverse=True)

    # -- Lecture ----------------------------------------------------------------------

    def count(self) -> int:
        return self._collection.count()

    def list_sources(self) -> list[str]:
        sources: set[str] = set()
        offset = 0
        while True:
            page = self._collection.get(
                offset=offset, limit=_ITER_PAGE_SIZE, include=["metadatas"]
            )
            sources.update(meta["source"] for meta in page["metadatas"])
            if len(page["ids"]) < _ITER_PAGE_SIZE:
                return sorted(sources)
            offset += _ITER_PAGE_SIZE

    def get_source_hash(self, source: str) -> str | None:
        found = self._collection.get(
            where={"source": source}, limit=1, include=["metadatas"]
        )
        if not found["ids"]:
            return None
        return found["metadatas"][0].get("file_hash")

    def iter_chunks(self) -> Iterator[Chunk]:
        offset = 0
        while True:
            page = self._collection.get(
                offset=offset,
                limit=_ITER_PAGE_SIZE,
                include=["documents", "metadatas"],
            )
            for chunk_id, document, metadata in zip(
                page["ids"], page["documents"], page["metadatas"], strict=True
            ):
                yield self._from_chroma(chunk_id, document, metadata)
            if len(page["ids"]) < _ITER_PAGE_SIZE:
                return
            offset += _ITER_PAGE_SIZE

    def get_embedding_model(self) -> str | None:
        return (self._collection.metadata or {}).get("embedding_model")

    def set_embedding_model(self, name: str) -> None:
        metadata = dict(self._collection.metadata or {})
        metadata["embedding_model"] = name
        self._collection.modify(metadata=metadata)

    # -- Internes -------------------------------------------------------------------------

    @staticmethod
    def _to_chroma_metadata(chunk: Chunk) -> dict:
        """Aplatit un Chunk en métadonnées Chroma (valeurs scalaires seulement)."""
        metadata: dict = {
            "source": chunk.source,
            "page": _PAGE_NULL if chunk.page is None else chunk.page,
            "chunk_index": chunk.index,
        }
        for key, value in chunk.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                metadata[key] = value
        return metadata

    @staticmethod
    def _from_chroma(chunk_id: str, document: str, metadata: dict) -> Chunk:
        page = metadata.get("page", _PAGE_NULL)
        raw_metadata = {
            key: value
            for key, value in metadata.items()
            if key not in {"source", "page", "chunk_index"}
        }
        return Chunk(
            id=chunk_id,
            text=document,
            source=metadata["source"],
            page=None if page == _PAGE_NULL else page,
            index=metadata.get("chunk_index", 0),
            metadata=json.loads(json.dumps(raw_metadata)) if raw_metadata else {},
        )
