"""Tests des fournisseurs d'embeddings (sans réseau : faux client injecté)."""

import pytest
from openai import OpenAIError

from rag_core.embeddings.factory import EmbeddingFactory
from rag_core.embeddings.fake import FakeEmbeddingProvider
from rag_core.embeddings.openai_compatible import OpenAICompatibleEmbeddings
from rag_core.exceptions import EmbeddingError
from rag_core.settings import Settings

# ---------------------------------------------------------------------------
# Doubles du SDK (attribut embeddings.create)
# ---------------------------------------------------------------------------


class _FakeEmbeddingItem:
    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding


class _FakeEmbeddingsResponse:
    def __init__(self, data: list[_FakeEmbeddingItem]) -> None:
        self.data = data


class FakeEmbeddingsClient:
    """Double minimal de client.embeddings.create : enregistre les lots."""

    def __init__(
        self,
        dimension: int = 4,
        error: Exception | None = None,
        wrong_count: bool = False,
    ) -> None:
        self._dimension = dimension
        self._error = error
        self._wrong_count = wrong_count
        self.batches: list[list[str]] = []
        self.embeddings = self  # le SDK appelle client.embeddings.create

    def create(self, model: str, input: list[str]):  # noqa: A002 — nom du SDK
        self.batches.append(list(input))
        if self._error is not None:
            raise self._error
        count = len(input) - 1 if self._wrong_count else len(input)
        return _FakeEmbeddingsResponse(
            [_FakeEmbeddingItem([0.1] * self._dimension) for _ in range(count)]
        )


# ---------------------------------------------------------------------------
# FakeEmbeddingProvider
# ---------------------------------------------------------------------------


def test_fake_provider_is_deterministic():
    provider = FakeEmbeddingProvider(dimension=16)
    first = provider.embed_query("le chat dort")
    second = provider.embed_query("le chat dort")
    assert first == second


def test_fake_provider_distinguishes_texts():
    provider = FakeEmbeddingProvider(dimension=16)
    assert provider.embed_query("chat") != provider.embed_query("voiture")


def test_fake_provider_properties():
    provider = FakeEmbeddingProvider(dimension=32)
    assert provider.model_name == "fake-embedding"
    vectors = provider.embed(["a", "b"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 32
    # vecteurs normalisés (norme 1)
    norm = sum(value**2 for value in vectors[0]) ** 0.5
    assert norm == pytest.approx(1.0, abs=1e-5)


# ---------------------------------------------------------------------------
# OpenAICompatibleEmbeddings avec faux client
# ---------------------------------------------------------------------------


def _make_provider(fake_client, batch_size=2):
    return OpenAICompatibleEmbeddings(
        "http://localhost:11434/v1", "ollama", "nomic-embed-text",
        batch_size=batch_size, client=fake_client,
    )


def test_openai_embeddings_splits_into_batches():
    fake = FakeEmbeddingsClient(dimension=4)
    provider = _make_provider(fake, batch_size=2)
    vectors = provider.embed(["a", "b", "c", "d", "e"])
    assert len(vectors) == 5
    assert fake.batches == [["a", "b"], ["c", "d"], ["e"]]  # 2 + 2 + 1


def test_openai_embeddings_model_name():
    provider = _make_provider(FakeEmbeddingsClient())
    assert provider.model_name == "nomic-embed-text"


def test_openai_embeddings_sdk_error_converted():
    fake = FakeEmbeddingsClient(error=OpenAIError("boom"))
    provider = _make_provider(fake)
    with pytest.raises(EmbeddingError):
        provider.embed(["a"])


def test_openai_embeddings_count_mismatch_detected():
    fake = FakeEmbeddingsClient(wrong_count=True)
    provider = _make_provider(fake)
    with pytest.raises(EmbeddingError, match="vecteurs"):
        provider.embed(["a", "b"])


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_embedding_factory_returns_configured_provider(monkeypatch):
    monkeypatch.setenv("EMBED_BASE_URL", "http://example.com/v1")
    monkeypatch.setenv("EMBED_MODEL", "mon-modele")
    monkeypatch.setenv("EMBED_BATCH_SIZE", "8")
    provider = EmbeddingFactory.create(Settings(_env_file=None))
    assert isinstance(provider, OpenAICompatibleEmbeddings)
    assert provider.model_name == "mon-modele"
