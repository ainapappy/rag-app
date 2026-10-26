"""Retriever : retrouve les chunks pertinents pour une question."""

from rag_core.embeddings.base import EmbeddingProvider
from rag_core.models import SearchResult
from rag_core.vectorstore.base import VectorStore


class Retriever:
    """Recherche sémantique : embed la requête, cherche, filtre, trie.

    Ne dépend que d'interfaces (`EmbeddingProvider`, `VectorStore`).
    """

    def __init__(
        self,
        embeddings: EmbeddingProvider,
        store: VectorStore,
        top_k: int,
        min_score: float,
    ) -> None:
        self._embeddings = embeddings
        self._store = store
        self._top_k = top_k
        self._min_score = min_score

    def retrieve(self, query: str) -> list[SearchResult]:
        """Renvoie au plus `top_k` résultats au-dessus de `min_score`, triés."""
        query_vector = self._embeddings.embed_query(query)
        results = self._store.search(query_vector, self._top_k)
        relevant = [result for result in results if result.score >= self._min_score]
        return sorted(relevant, key=lambda result: result.score, reverse=True)
