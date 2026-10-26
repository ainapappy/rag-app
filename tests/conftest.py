"""Fixtures partagées : faux LLM, faux embeddings, store temporaire, conteneur."""

import pytest

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
