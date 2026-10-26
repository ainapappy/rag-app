"""Recherche hybride : fusion RRF du classement vectoriel et du BM25.

RRF (*Reciprocal Rank Fusion*) : score = Σ 1/(60 + rang) sur chaque liste.
Le filtre `min_score` s'applique au score vectoriel d'origine ; un chunk
trouvé uniquement par BM25 reste éligible (pas de score vectoriel à filtrer).
"""

from rag_core.embeddings.base import EmbeddingProvider
from rag_core.models import SearchResult
from rag_core.retrieval.bm25 import Bm25Index
from rag_core.vectorstore.base import VectorStore

RRF_K = 60  # constante classique de la formule RRF


class HybridRetriever:
    """Même interface publique que `Retriever` : une seule méthode `retrieve`."""

    def __init__(
        self,
        embeddings: EmbeddingProvider,
        store: VectorStore,
        bm25: Bm25Index,
        top_k: int,
        min_score: float,
    ) -> None:
        self.embeddings = embeddings
        self.store = store
        self.bm25 = bm25
        self.top_k = top_k
        self.min_score = min_score

    def retrieve(self, query: str) -> list[SearchResult]:
        """Fusionne les deux classements par RRF et renvoie le top_k."""
        query_vector = self.embeddings.embed_query(query)
        vector_results = [
            result
            for result in self.store.search(query_vector, self.top_k)
            if result.score >= self.min_score
        ]
        # BM25 renvoie des (chunk, score) : aligner sur SearchResult.
        bm25_results = [
            SearchResult(chunk=chunk, score=score)
            for chunk, score in self.bm25.search(query, self.top_k)
        ]

        rrf_scores: dict[str, float] = {}
        chunks: dict[str, SearchResult] = {}
        for ranking in (vector_results, bm25_results):
            for rank, result in enumerate(ranking, start=1):
                rrf_scores[result.chunk.id] = rrf_scores.get(result.chunk.id, 0.0) + 1.0 / (
                    RRF_K + rank
                )
                chunks.setdefault(result.chunk.id, result)

        fused = sorted(
            chunks.values(), key=lambda result: rrf_scores[result.chunk.id], reverse=True
        )
        return fused[: self.top_k]
