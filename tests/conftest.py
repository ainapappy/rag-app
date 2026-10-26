"""Fixtures partagées : faux LLM, faux embeddings, store temporaire, conteneur."""

import pytest

from chatbot.services import DocumentIndexingService
from rag_core.container import Container, reset_container
from rag_core.embeddings.fake import FakeEmbeddingProvider
from rag_core.llm.fake import FakeLLM
from rag_core.settings import Settings, get_settings
from rag_core.vectorstore.simple import SimpleVectorStore


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def fake_embeddings() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider(dimension=32)


@pytest.fixture
def tmp_store(tmp_path) -> SimpleVectorStore:
    """Store « simple » isolé dans un dossier temporaire de test."""
    return SimpleVectorStore(tmp_path / "index")


@pytest.fixture
def container(fake_llm, fake_embeddings, tmp_store) -> Container:
    """Conteneur avec les faux injectés : aucun réseau, aucun index réel."""
    return Container(
        Settings(_env_file=None),
        llm=fake_llm,
        embeddings=fake_embeddings,
        store=tmp_store,
    )


@pytest.fixture(autouse=True)
def _reset_container_cache():
    """Évite l'état global : le conteneur applicatif est reconstruit à chaque test."""
    reset_container()
    get_settings.cache_clear()
    yield
    reset_container()
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Fixtures Django (admin, services)
# ---------------------------------------------------------------------------


@pytest.fixture
def media_root(tmp_path, settings):
    """Redirige MEDIA_ROOT vers un dossier temporaire (aucun vrai fichier écrit)."""
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


class FakeIngestionPipeline:
    """Remplace `container.ingestion_pipeline` : simule rag_core sans réseau."""

    def __init__(self, error: Exception | None = None, chunks_count: int = 3) -> None:
        self.calls: list[tuple[str, str | None, bool]] = []
        self.removed: list[str] = []
        self.chunks_count = chunks_count
        self.error = error

    def ingest_file(self, path, source=None, force=False):
        self.calls.append((str(path), source, force))
        if self.error is not None:
            raise self.error
        from rag_core.pipeline.ingestion import IngestionReport

        return IngestionReport(source=source or "x", chunks_count=self.chunks_count)

    def remove_source(self, source: str) -> int:
        self.removed.append(source)
        return 1


class FakeContainer:
    """Conteneur minimal avec uniquement `ingestion_pipeline`."""

    def __init__(self, pipeline: FakeIngestionPipeline) -> None:
        self.ingestion_pipeline = pipeline


@pytest.fixture
def fake_pipeline() -> FakeIngestionPipeline:
    return FakeIngestionPipeline()


@pytest.fixture
def indexing_service(fake_pipeline) -> DocumentIndexingService:
    """Service branché sur un conteneur factice (aucun index réel)."""
    return DocumentIndexingService(container=FakeContainer(fake_pipeline))


@pytest.fixture
def patched_container(monkeypatch, fake_pipeline) -> FakeContainer:
    """Remplace le conteneur par défaut des services (admin → jamais de réseau).

    Sans ce patch, `DocumentIndexingService()` sans argument appellerait le
    vrai `get_container()` (Ollama + data/index) pendant les tests.
    """
    import chatbot.services as services_module

    fake = FakeContainer(fake_pipeline)
    monkeypatch.setattr(services_module, "get_container", lambda: fake)
    return fake


# ---------------------------------------------------------------------------
# Fixtures chat (pipeline RAG enregistrant ses appels)
# ---------------------------------------------------------------------------


class RecordingRagPipeline:
    """Remplace `container.rag_pipeline` : réponses fixes, appels enregistrés."""

    def __init__(self, text: str = "Réponse de test.", found: bool = True, error=None) -> None:
        self.calls: list[tuple[str, tuple]] = []
        self.text = text
        self.found = found
        self.error = error
        self.sources = ()  # tuple de Source (vide par défaut)

    def ask(self, question: str, history: tuple = ()):
        self.calls.append((question, history))
        if self.error is not None:
            raise self.error
        from rag_core.models import Answer

        return Answer(text=self.text, sources=self.sources, found=self.found)

    def ask_stream(self, question: str, history: tuple = ()):
        self.calls.append((question, history))
        if self.error is not None:
            raise self.error
        from rag_core.models import StreamedAnswer

        tokens = iter([self.text]) if self.found else iter([self.text])
        return StreamedAnswer(sources=self.sources, found=self.found, tokens=tokens)


class FakeChatContainer:
    """Conteneur minimal pour ChatService : settings + rag_pipeline."""

    def __init__(self, pipeline: RecordingRagPipeline, settings=None) -> None:
        self.rag_pipeline = pipeline
        self._settings = settings or Settings(_env_file=None)

    @property
    def settings(self):
        return self._settings


@pytest.fixture
def rag_pipeline() -> RecordingRagPipeline:
    return RecordingRagPipeline()


@pytest.fixture
def chat_container(rag_pipeline) -> FakeChatContainer:
    return FakeChatContainer(rag_pipeline)


@pytest.fixture
def patched_chat_container(monkeypatch, chat_container) -> FakeChatContainer:
    """Remplace le conteneur utilisé par `ChatService()` dans les vues."""
    import chatbot.services as services_module

    monkeypatch.setattr(services_module, "get_container", lambda: chat_container)
    return chat_container


@pytest.fixture
def user(django_user_model):
    """Utilisateur standard (≈ factory User de Laravel)."""
    return django_user_model.objects.create_user("alice", password="test1234")
