"""Factory du fournisseur d'embeddings : choix selon les Settings."""

from rag_core.embeddings.base import EmbeddingProvider
from rag_core.embeddings.openai_compatible import OpenAICompatibleEmbeddings
from rag_core.settings import Settings


class EmbeddingFactory:
    """Crée le fournisseur d'embeddings configuré par `Settings`."""

    @staticmethod
    def create(settings: Settings) -> EmbeddingProvider:
        """Retourne un EmbeddingProvider prêt à l'emploi."""
        return OpenAICompatibleEmbeddings(
            base_url=settings.embed_base_url,
            api_key=settings.embed_api_key,
            model=settings.embed_model,
            batch_size=settings.embed_batch_size,
        )
