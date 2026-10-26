"""Exceptions métier du cœur RAG (hiérarchie sous RagError)."""


class RagError(Exception):
    """Erreur de base de toutes les exceptions métier du cœur RAG."""


class ConfigError(RagError):
    """Configuration invalide ou incomplète (variables d'environnement, Settings)."""


class LLMError(RagError):
    """Le client LLM n'a pas pu obtenir de réponse (connexion, API, modèle)."""


class EmbeddingError(RagError):
    """Échec lors du calcul des embeddings."""


class LoaderError(RagError):
    """Échec lors du chargement d'un document."""


class UnsupportedFileTypeError(LoaderError):
    """Type de fichier non pris en charge par les loaders."""


class VectorStoreError(RagError):
    """Erreur du magasin vectoriel (lecture, écriture, index corrompu)."""


class EmbeddingModelMismatchError(VectorStoreError):
    """L'index a été construit avec un autre modèle d'embeddings."""
