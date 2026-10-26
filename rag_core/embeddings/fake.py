"""Embeddings déterministes pour les tests : aucun réseau."""

import hashlib

import numpy as np

from rag_core.embeddings.base import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    """Fournisseur factice : même texte → même vecteur, déterministe.

    Les vecteurs dérivent du hachage sha256 du texte (seed du générateur
    aléatoire), normalisés. Pas de sémantique réelle, mais suffisant pour
    tester les stores et les pipelines sans Ollama.
    """

    def __init__(self, dimension: int = 64) -> None:
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        return "fake-embedding"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._one(text)

    def _one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "big"))
        vector = rng.standard_normal(self._dimension)
        norm = np.linalg.norm(vector)
        if norm == 0:  # improbable, mais évite la division par zéro
            return vector.tolist()
        return (vector / norm).tolist()
