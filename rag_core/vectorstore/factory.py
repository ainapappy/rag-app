"""Factory du magasin vectoriel : `simple` (défaut) ou `chroma`."""

from pathlib import Path

from rag_core.exceptions import VectorStoreError
from rag_core.settings import Settings
from rag_core.vectorstore.base import VectorStore
from rag_core.vectorstore.simple import SimpleVectorStore


class VectorStoreFactory:
    """Choisit l'implémentation du store selon `VECTOR_STORE`.

    Changer d'implémentation ne demande aucune modification de code :
    juste la variable d'environnement.
    """

    @staticmethod
    def create(settings: Settings) -> VectorStore:
        """Retourne le VectorStore configuré (dossier créé si besoin)."""
        path = Path(settings.vector_store_path)
        if settings.vector_store == "simple":
            return SimpleVectorStore(path)
        if settings.vector_store == "chroma":
            # Import paresseux : chromadb peut ne pas être installé.
            from rag_core.vectorstore.chroma import ChromaVectorStore

            return ChromaVectorStore(path)
        raise VectorStoreError(
            f"Vector store inconnu : {settings.vector_store!r} (attendu : simple, chroma)"
        )
