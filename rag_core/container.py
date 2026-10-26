"""Conteneur de services (≈ Service Container / AppServiceProvider de Laravel).

Assemble toutes les dépendances à partir des Settings. Les classes métier
ne construisent jamais leurs dépendances elles-mêmes. Les paramètres nommés
permettent d'injecter des faux en test (≈ `$app->instance()`).
"""

from functools import cached_property

from rag_core.chunking.factory import ChunkerFactory
from rag_core.embeddings.factory import EmbeddingFactory
from rag_core.llm.factory import LLMFactory
from rag_core.loaders.factory import LoaderFactory
from rag_core.pipeline.ingestion import IngestionPipeline
from rag_core.settings import Settings, get_settings
from rag_core.vectorstore.factory import VectorStoreFactory


class Container:
    """Construit et met en cache les services du cœur RAG (paresseux)."""

    def __init__(
        self,
        settings: Settings,
        *,
        llm=None,
        embeddings=None,
        store=None,
    ) -> None:
        self._settings = settings
        self._llm = llm
        self._embeddings = embeddings
        self._store = store

    @property
    def llm(self):
        """Client de chat (lazy : créé au premier accès)."""
        if self._llm is None:
            self._llm = LLMFactory.create(self._settings)
        return self._llm

    @property
    def embeddings(self):
        """Fournisseur d'embeddings (lazy)."""
        if self._embeddings is None:
            self._embeddings = EmbeddingFactory.create(self._settings)
        return self._embeddings

    @property
    def store(self):
        """Magasin vectoriel (lazy)."""
        if self._store is None:
            self._store = VectorStoreFactory.create(self._settings)
        return self._store

    @cached_property
    def loader_factory(self) -> type[LoaderFactory]:
        """Factory des chargeurs de documents."""
        return LoaderFactory

    @cached_property
    def chunker(self):
        """Chunker configuré (lazy)."""
        return ChunkerFactory.create(self._settings)

    @cached_property
    def ingestion_pipeline(self) -> IngestionPipeline:
        """Pipeline d'ingestion complet (lazy)."""
        return IngestionPipeline(
            loader_factory=self.loader_factory,
            chunker=self.chunker,
            embeddings=self.embeddings,
            store=self.store,
            batch_size=self._settings.embed_batch_size,
        )

    # La propriété `rag_pipeline` sera ajoutée en phase 05.


# Cache module-level du conteneur (≈ singleton applicatif).
_container: Container | None = None


def get_container() -> Container:
    """Retourne le conteneur applicatif, construit au premier appel."""
    global _container
    if _container is None:
        _container = Container(get_settings())
    return _container


def reset_container() -> None:
    """Force la reconstruction du conteneur au prochain `get_container()`
    (indispensable entre les tests pour éviter l'état global résiduel)."""
    global _container
    _container = None
