"""Tests des clients LLM : FakeLLM, OpenAICompatibleLLM (faux client injecté), factory."""

import pytest
from openai import OpenAIError

from rag_core.exceptions import LLMError
from rag_core.llm.factory import LLMFactory
from rag_core.llm.fake import FakeLLM
from rag_core.llm.openai_compatible import OpenAICompatibleLLM
from rag_core.models import ChatMessage
from rag_core.settings import Settings, get_settings

# ---------------------------------------------------------------------------
# Doubles du SDK OpenAI (le strict minimum attendu par OpenAICompatibleLLM)
# ---------------------------------------------------------------------------


class _FakeMessage:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _FakeDelta:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, message=None, delta=None) -> None:
        self.message = message
        self.delta = delta


class _FakeResponse:
    def __init__(self, choices) -> None:
        self.choices = choices


class FakeOpenAIClient:
    """Double minimal du client openai.OpenAI (attribut chat.completions.create)."""

    def __init__(
        self,
        content: str = "Bonjour !",
        stream_chunks: list[str | None] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._content = content
        self._stream_chunks = stream_chunks if stream_chunks is not None else list(content)
        self._error = error
        self.last_kwargs: dict | None = None
        self.chat = self  # le SDK appelle client.chat.completions.create

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self._error is not None:
            raise self._error
        if kwargs.get("stream"):
            return iter([
                _FakeResponse([_FakeChoice(delta=_FakeDelta(c))]) for c in self._stream_chunks
            ])
        return _FakeResponse([_FakeChoice(message=_FakeMessage(self._content))])


# ---------------------------------------------------------------------------
# FakeLLM
# ---------------------------------------------------------------------------


def test_fake_llm_returns_programmed_responses_in_order():
    llm = FakeLLM(responses=["première", "deuxième"])
    messages = [ChatMessage(role="user", content="q1")]
    assert llm.chat(messages) == "première"
    assert llm.chat(messages) == "deuxième"
    assert llm.chat(messages) == "Réponse par défaut du faux LLM."


def test_fake_llm_records_calls():
    llm = FakeLLM()
    messages = [ChatMessage(role="user", content="salut")]
    llm.chat(messages)
    assert llm.calls == [messages]


def test_fake_llm_stream_splits_response():
    llm = FakeLLM(responses=["abcdefghij"])
    fragments = list(llm.stream([ChatMessage(role="user", content="q")]))
    assert "".join(fragments) == "abcdefghij"
    assert len(fragments) > 1  # bien découpée en petits morceaux


# ---------------------------------------------------------------------------
# OpenAICompatibleLLM avec faux client injecté
# ---------------------------------------------------------------------------


def test_openai_compatible_chat_returns_text():
    fake = FakeOpenAIClient(content="Salut !")
    llm = OpenAICompatibleLLM("http://localhost:11434/v1", "ollama", "llama3.2:3b", client=fake)
    answer = llm.chat([ChatMessage(role="user", content="bonjour")])
    assert answer == "Salut !"
    assert fake.last_kwargs["model"] == "llama3.2:3b"
    assert fake.last_kwargs["messages"] == [{"role": "user", "content": "bonjour"}]


def test_openai_compatible_stream_yields_non_empty_deltas():
    fake = FakeOpenAIClient(stream_chunks=["Hel", "lo", None, " !"])
    llm = OpenAICompatibleLLM("http://localhost:11434/v1", "ollama", "m", client=fake)
    assert list(llm.stream([ChatMessage(role="user", content="q")])) == ["Hel", "lo", " !"]


def test_openai_compatible_converts_error_to_llm_error():
    fake = FakeOpenAIClient(error=OpenAIError("connexion refusée"))
    llm = OpenAICompatibleLLM("http://localhost:11434/v1", "ollama", "m", client=fake)
    with pytest.raises(LLMError):
        llm.chat([ChatMessage(role="user", content="q")])


def test_openai_compatible_error_message_is_french_and_clear():
    fake = FakeOpenAIClient(error=OpenAIError("boom"))
    llm = OpenAICompatibleLLM("http://localhost:11434/v1", "ollama", "m", client=fake)
    with pytest.raises(LLMError, match="Erreur du LLM"):
        llm.chat([ChatMessage(role="user", content="q")])


# ---------------------------------------------------------------------------
# Factory et ChatMessage
# ---------------------------------------------------------------------------


def test_factory_returns_configured_client():
    settings = Settings(_env_file=None)
    llm = LLMFactory.create(settings)
    assert isinstance(llm, OpenAICompatibleLLM)
    assert llm._model == settings.llm_model
    assert llm._temperature == settings.llm_temperature


def test_chat_message_rejects_invalid_role():
    with pytest.raises(ValueError, match="Rôle invalide"):
        ChatMessage(role="moderator", content="x")


# ---------------------------------------------------------------------------
# Test d'intégration réel (ignoré par défaut : pytest -m integration)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_real_ollama_chat():
    """Interroge réellement Ollama — nécessite `ollama serve` et les modèles."""
    llm = LLMFactory.create(get_settings())
    answer = llm.chat([ChatMessage(role="user", content="Dis bonjour en une phrase")])
    assert answer.strip()
