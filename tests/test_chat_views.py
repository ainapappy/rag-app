"""Tests des vues de chat : authentification, isolation, streaming, CSRF."""


import pytest
from django.test import Client
from django.urls import reverse

from chatbot.models import Conversation
from chatbot.services import ChatService

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user("alice", password="test1234")


@pytest.fixture
def other_logged_client(client, other_user):
    """Client connecté à BOB (pour tester l'isolation des conversations)."""
    client.force_login(other_user)
    return client


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user("bob", password="test1234")


@pytest.fixture
def logged_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def conversation(user) -> Conversation:
    return Conversation.objects.create(user=user, title="Ma conversation")


# ---------------------------------------------------------------------------
# Authentification et isolation
# ---------------------------------------------------------------------------


def test_anonymous_redirects_to_login(client):
    response = client.get(reverse("chat"))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_logged_user_sees_chat_page(logged_client):
    response = logged_client.get(reverse("chat"))
    assert response.status_code == 200
    # La coquille HTML contient le point de montage de l'application Vue.
    assert 'id="chat-app"' in response.content.decode()


def test_other_users_conversation_returns_404(other_logged_client, conversation):
    """Bob ne peut ni voir la conversation d'Alice, ni l'alimenter."""
    url = reverse("chat_detail", args=[conversation.pk])
    assert other_logged_client.get(url).status_code == 404
    send_url = reverse("chat_send", args=[conversation.pk])
    response = other_logged_client.post(send_url, {"question": "x"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Envoi d'un message
# ---------------------------------------------------------------------------


def test_send_streaming_response(
    logged_client, conversation, patched_chat_container, rag_pipeline
):
    rag_pipeline.sources = ()  # pas de sources : simple
    response = logged_client.post(
        reverse("chat_send", args=[conversation.pk]), {"question": "bonjour"}
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "text/event-stream"
    assert response["Cache-Control"] == "no-cache"
    body = b"".join(response.streaming_content).decode()
    events = [line for line in body.split("\n") if line.startswith("event: ")]
    assert events == ["event: sources", "event: token", "event: done"]
    # Deux messages enregistrés (question + réponse).
    assert conversation.messages.count() == 2


def test_send_without_streaming_returns_json(
    logged_client, conversation, patched_chat_container, rag_pipeline, monkeypatch
):
    """Mode STREAMING_ENABLED=False : un JSON unique (pas de fragment HTML)."""
    monkeypatch.setenv("STREAMING_ENABLED", "false")
    from rag_core.settings import get_settings

    get_settings.cache_clear()
    try:
        response = logged_client.post(
            reverse("chat_send", args=[conversation.pk]), {"question": "bonjour"}
        )
    finally:
        get_settings.cache_clear()
    assert response.status_code == 200
    assert "application/json" in response["Content-Type"]
    payload = response.json()
    assert payload["role"] == "assistant"
    assert payload["content"] == "Réponse de test."
    assert isinstance(payload["sources"], list)
    assert conversation.messages.count() == 2


def test_send_requires_csrf(conversation, user, patched_chat_container):
    """Client CSRF strict : POST sans jeton → 403."""
    strict_client = Client(enforce_csrf_checks=True)
    strict_client.force_login(user)
    response = strict_client.post(
        reverse("chat_send", args=[conversation.pk]), {"question": "bonjour"}
    )
    assert response.status_code == 403


def test_send_empty_question_rejected(logged_client, conversation, patched_chat_container):
    response = logged_client.post(reverse("chat_send", args=[conversation.pk]), {"question": "  "})
    assert response.status_code == 400


def test_conversation_detail_shows_history(logged_client, conversation, rag_pipeline):
    """Le deep-link /chat/<pk>/ rend la coquille et l'historique est conservé."""
    service = ChatService(container=_container_with(rag_pipeline))
    service.ask(conversation, "une question")
    response = logged_client.get(reverse("chat_detail", args=[conversation.pk]))
    assert response.status_code == 200
    assert 'id="chat-app"' in response.content.decode()
    # L'historique est conservé au rechargement.
    assert conversation.messages.count() == 2


def _container_with(pipeline):
    from rag_core.settings import Settings
    from tests.conftest import FakeChatContainer

    return FakeChatContainer(pipeline, Settings(_env_file=None))
