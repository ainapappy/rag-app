"""Interface abstraite du magasin vectoriel (méthodes exactes du contrat)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path

from rag_core.models import Chunk, SearchResult


class VectorStore(ABC):
    """Contrat commun aux magasins de vecteurs (`simple`, `chroma`).

    Les deux implémentations doivent être interchangeables : même
    interface, même comportement observable.
    """

    @abstractmethod
    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Ajoute (ou met à jour) des chunks avec leurs vecteurs (upsert par id)."""

    @abstractmethod
    def search(self, query_embedding: list[float], top_k: int) -> list[SearchResult]:
        """Renvoie les `top_k` chunks les plus proches, triés par score décroissant."""

    @abstractmethod
    def delete_by_source(self, source: str) -> int:
        """Supprime tous les chunks d'une source ; renvoie le nombre supprimé."""

    @abstractmethod
    def count(self) -> int:
        """Nombre total de chunks dans l'index."""

    @abstractmethod
    def list_sources(self) -> list[str]:
        """Liste triée des sources présentes dans l'index."""

    @abstractmethod
    def get_source_hash(self, source: str) -> str | None:
        """Hash du fichier d'une source (clé `file_hash`), None si inconnue."""

    @abstractmethod
    def iter_chunks(self) -> Iterator[Chunk]:
        """Itère sur tous les chunks de l'index."""

    @abstractmethod
    def get_embedding_model(self) -> str | None:
        """Nom du modèle d'embeddings utilisé pour construire l'index."""

    @abstractmethod
    def set_embedding_model(self, name: str) -> None:
        """Enregistre le nom du modèle d'embeddings de l'index."""

    @abstractmethod
    def clear(self) -> None:
        """Vide entièrement l'index (chunks et métadonnées)."""


def ensure_directory(path: Path) -> Path:
    """Crée le dossier d'index si besoin et le renvoie (utilitaire partagé)."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path
