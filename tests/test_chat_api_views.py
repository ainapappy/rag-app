"""Tests des endpoints JSON de l'interface Vue (session + CSRF, phase 11)."""

import json

import pytest
from django.test import Client
from django.urls import reverse

from chatbot.models import Conversation, Message

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user("alice", password="test1234")


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
# Liste et création
# ---------------------------------------------------------------------------


def test_list_conversations_empty(logged_client):
    response = logged_client.get(reverse("chat_api_conversations"))
    assert response.status_code == 200
    assert response.json() == {"conversations": []}


def test_list_conversations_returns_own_only(logged_client, conversation, other_user):
    Conversation.objects.create(user=other_user, title="De Bob")
    response = logged_client.get(reverse("chat_api_conversations"))
    data = response.json()
    assert [c["id"] for c in data["conversations"]] == [conversation.pk]
    assert data["conversations"][0]["title"] == "Ma conversation"


def test_create_conversation(logged_client):
    response = logged_client.post(
        reverse("chat_api_conversations"),
        data=json.dumps({"title": "Nouvelle"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    conversation = Conversation.objects.get()
    assert conversation.user.username == "alice"
    assert conversation.title == "Nouvelle"
    assert response.json()["id"] == conversation.pk


def test_create_conversation_without_body(logged_client):
    """POST avec corps vide : création avec titre vide (posé à la première question)."""
    response = logged_client.post(
        reverse("chat_api_conversations"), data="", content_type="application/json"
    )
    assert response.status_code == 201
    assert Conversation.objects.get().title == ""


def test_create_conversation_invalid_json(logged_client):
    response = logged_client.post(
        reverse("chat_api_conversations"),
        data="not json",
        content_type="application/json",
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Détail, suppression, isolation
# ---------------------------------------------------------------------------


def test_detail_returns_messages(logged_client, conversation):
    Message.objects.create(conversation=conversation, role="user", content="bonjour")
    Message.objects.create(
        conversation=conversation, role="assistant", content="salut", sources=[]
    )
    response = logged_client.get(
        reverse("chat_api_conversation_detail", args=[conversation.pk])
    )
    assert response.status_code == 200
    data = response.json()
    assert data["conversation"]["title"] == "Ma conversation"
    assert [m["role"] for m in data["messages"]] == ["user", "assistant"]
    assert data["messages"][0]["content"] == "bonjour"


def test_delete_own_conversation(logged_client, conversation):
    response = logged_client.delete(
        reverse("chat_api_conversation_detail", args=[conversation.pk])
    )
    assert response.status_code == 204
    assert not Conversation.objects.filter(pk=conversation.pk).exists()


def test_anonymous_redirects_to_login(client):
    response = client.get(reverse("chat_api_conversations"))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_other_users_conversation_returns_404(client, other_user, conversation):
    """Bob ne peut ni lire, ni supprimer la conversation d'Alice."""
    client.force_login(other_user)
    url = reverse("chat_api_conversation_detail", args=[conversation.pk])
    assert client.get(url).status_code == 404
    assert client.delete(url).status_code == 404


def test_csrf_required(conversation, user):
    """Client CSRF strict : POST/DELETE sans jeton → 403."""
    strict_client = Client(enforce_csrf_checks=True)
    strict_client.force_login(user)
    assert (
        strict_client.post(reverse("chat_api_conversations")).status_code == 403
    )
    assert (
        strict_client.delete(
            reverse("chat_api_conversation_detail", args=[conversation.pk])
        ).status_code
        == 403
    )
