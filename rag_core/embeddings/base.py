"""Interface abstraite d'un fournisseur d'embeddings (≈ interface PHP)."""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Contrat commun à tous les fournisseurs de vecteurs de texte."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Nom du modèle d'embeddings (ex. « nomic-embed-text »)."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Calcule les vecteurs d'une liste de textes (même ordre, même taille)."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Calcule le vecteur d'une requête unique."""
