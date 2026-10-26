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
from rag_core.pipeline.rag import RagPipeline
from rag_core.prompting.prompt_builder import PromptBuilder
from rag_core.prompting.query_rewriter import QueryRewriter
from rag_core.retrieval.retriever import Retriever
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

    @cached_property
    def retriever(self):
        """Retriever vectoriel ou hybride selon RETRIEVER (lazy)."""
        if self._settings.retriever == "hybrid":
            from rag_core.retrieval.bm25 import Bm25Index
            from rag_core.retrieval.hybrid import HybridRetriever

            bm25 = Bm25Index.from_store(self.store)
            return HybridRetriever(
                self.embeddings,
                self.store,
                bm25,
                self._settings.top_k,
                self._settings.min_score,
            )
        return Retriever(
            self.embeddings, self.store, self._settings.top_k, self._settings.min_score
        )

    @cached_property
    def prompt_builder(self):
        """Constructeur de prompts RAG (lazy)."""
        return PromptBuilder()

    @cached_property
    def rewriter(self):
        """Reformulateur de questions de suivi (lazy)."""
        return QueryRewriter(self.llm)

    @cached_property
    def rag_pipeline(self):
        """Pipeline RAG complet (retrieve → prompt → LLM), lazy."""
        return RagPipeline(self.retriever, self.prompt_builder, self.llm, self.rewriter)

    @property
    def settings(self) -> Settings:
        """Settings portés par ce conteneur (ex. HISTORY_WINDOW pour le chat)."""
        return self._settings


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
