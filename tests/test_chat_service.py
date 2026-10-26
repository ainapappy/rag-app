"""Tests du ChatService : messages persistés, fenêtre d'historique, SSE."""

import json
from dataclasses import asdict

import pytest

from chatbot.models import Conversation, Message
from chatbot.services import ChatService
from rag_core.exceptions import EmbeddingError
from rag_core.models import Source
from tests.conftest import RecordingRagPipeline

pytestmark = pytest.mark.django_db


def _conversation(user) -> Conversation:
    return Conversation.objects.create(user=user)


# ---------------------------------------------------------------------------
# ask
# ---------------------------------------------------------------------------


def test_ask_saves_user_and_assistant_messages(user, chat_container, rag_pipeline):
    conversation = _conversation(user)
    service = ChatService(container=chat_container)
    answer = service.ask(conversation, "Combien de jours de congés ?")
    roles = list(conversation.messages.values_list("role", flat=True))
    assert roles == ["user", "assistant"]
    assert answer.role == "assistant"
    assert answer.content == "Réponse de test."


def test_ask_sets_title_from_first_question(user, chat_container):
    conversation = _conversation(user)
    service = ChatService(container=chat_container)
    service.ask(conversation, "Une première question très longue qui définit le titre")
    conversation.refresh_from_db()
    assert conversation.title == "Une première question très longue qui définit le titre"[:60]


def test_history_window_is_applied(user):
    """Au-delà de HISTORY_WINDOW, seuls les derniers messages sont envoyés."""

    conversation = _conversation(user)
    for i in range(8):
        Message.objects.create(
            conversation=conversation,
            role="user" if i % 2 == 0 else "assistant",
            content=f"message {i}",
        )
    pipeline = RecordingRagPipeline()
    container = FakeContainerWithWindow(pipeline, history_window=3)
    service = ChatService(container=container)
    service.ask(conversation, "nouvelle question")
    sent_history = pipeline.calls[0][1]
    assert len(sent_history) == 3
    # Les 3 derniers messages avant la question (5..7), pas la question elle-même.
    assert [message.content for message in sent_history] == [
        "message 5",
        "message 6",
        "message 7",
    ]


class FakeContainerWithWindow:
    """Conteneur avec HISTORY_WINDOW réduit pour tester la fenêtre."""

    def __init__(self, pipeline, history_window: int) -> None:
        from rag_core.settings import Settings

        self.rag_pipeline = pipeline
        self._settings = Settings(_env_file=None, history_window=history_window)

    @property
    def settings(self):
        return self._settings


def test_ask_serializes_sources(user, chat_container, rag_pipeline):
    source = Source(source="conges.txt", page=2, score=0.85, excerpt="25 jours annuels")
    rag_pipeline.sources = (source,)
    conversation = _conversation(user)
    service = ChatService(container=chat_container)
    answer = service.ask(conversation, "question")
    assert answer.sources == [asdict(source)]


def test_ask_not_found_stores_no_answer_message(user, rag_pipeline):
    rag_pipeline.found = False
    rag_pipeline.text = "Je n'ai pas trouvé cette information dans les documents."
    conversation = _conversation(user)
    service = ChatService(container=FakeChatWindowDefault(pipeline=rag_pipeline))
    answer = service.ask(conversation, "question hors sujet")
    assert answer.content == "Je n'ai pas trouvé cette information dans les documents."
    assert answer.sources == []


class FakeChatWindowDefault:
    """Alias de conteneur standard (settings par défaut du contrat)."""

    def __init__(self, pipeline) -> None:
        from rag_core.settings import Settings

        self.rag_pipeline = pipeline
        self._settings = Settings(_env_file=None)

    @property
    def settings(self):
        return self._settings


# ---------------------------------------------------------------------------
# stream (SSE)
# ---------------------------------------------------------------------------


def _parse_sse(chunks: list[str]) -> list[tuple[str, str]]:
    """Reconstitue les événements (event, data) depuis les morceaux générés."""
    events: list[tuple[str, str]] = []
    for raw in "".join(chunks).split("\n\n"):
        name, data = "", ""
        for line in raw.split("\n"):
            if line.startswith("event: "):
                name = line[7:]
            if line.startswith("data: "):
                data = line[6:]
        if name:
            events.append((name, data))
    return events


def test_stream_emits_sources_tokens_done_in_order(user, chat_container, rag_pipeline):
    rag_pipeline.sources = (Source(source="doc.txt", page=1, score=0.9, excerpt="extrait"),)
    conversation = _conversation(user)
    service = ChatService(container=chat_container)
    chunks = list(service.stream(conversation, "bonjour"))
    events = _parse_sse(chunks)
    names = [name for name, _ in events]
    assert names[0] == "sources"
    assert "token" in names
    assert names[-1] == "done"
    # La réponse est bien enregistrée à la fin.
    assistant = Message.objects.filter(conversation=conversation, role="assistant").get()
    assert assistant.content == "Réponse de test."
    assert assistant.sources[0]["source"] == "doc.txt"


def test_stream_saves_partial_text_if_error(user, rag_pipeline):
    """Le bloc finally conserve le texte reçu avant l'erreur."""
    conversation = _conversation(user)
    pipeline = RecordingRagPipeline(text="partiel ")
    service = ChatService(container=FakeChatWindowDefault(pipeline=pipeline))
    # On simule une erreur en cours de génération : tokens générateur qui lève.
    def failing_tokens():
        yield "partiel "
        raise EmbeddingError("réseau coupé")

    from rag_core.models import StreamedAnswer

    def ask_stream(question, history=()):
        pipeline.calls.append((question, history))
        return StreamedAnswer(sources=(), found=True, tokens=failing_tokens())

    pipeline.ask_stream = ask_stream
    chunks = list(service.stream(conversation, "question"))
    events = _parse_sse(chunks)
    names = [name for name, _ in events]
    assert "error" in names
    assistant = Message.objects.filter(conversation=conversation, role="assistant").get()
    assert assistant.content == "partiel "  # texte partiel conservé


def test_stream_rag_error_emits_error_event(user, rag_pipeline):
    rag_pipeline.error = EmbeddingError("Ollama arrêté")
    conversation = _conversation(user)
    service = ChatService(container=FakeChatWindowDefault(pipeline=rag_pipeline))
    events = _parse_sse(list(service.stream(conversation, "question")))
    parsed = [(name, json.loads(data)) for name, data in events]
    assert ("error", {"message": "Ollama arrêté"}) in parsed
    assistant = Message.objects.filter(conversation=conversation, role="assistant").get()
    assert assistant.content == ""  # rien reçu : message vide mais persisté


def test_stream_not_found_yields_no_answer_token(user, rag_pipeline):
    rag_pipeline.found = False
    rag_pipeline.text = "Je n'ai pas trouvé cette information dans les documents."
    conversation = _conversation(user)
    service = ChatService(container=FakeChatWindowDefault(pipeline=rag_pipeline))
    events = _parse_sse(list(service.stream(conversation, "question hors sujet")))
    names = [name for name, _ in events]
    assert names == ["sources", "token", "done"]
