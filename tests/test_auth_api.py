"""Tests des endpoints d'authentification JSON pour le front Vue (phase 11)."""

import json

import pytest
from django.conf import settings
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user("alice", password="test1234")


def _post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


# ---------------------------------------------------------------------------
# État de session (me)
# ---------------------------------------------------------------------------


def test_me_anonymous(client):
    """Public, jamais de 401 ; pose le cookie CSRF pour les POST ultérieurs."""
    response = client.get(reverse("api_me"))
    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "username": None}
    assert "csrftoken" in response.cookies


def test_me_authenticated(client, user):
    client.force_login(user)
    response = client.get(reverse("api_me"))
    assert response.json() == {"authenticated": True, "username": "alice"}


# ---------------------------------------------------------------------------
# Connexion / déconnexion
# ---------------------------------------------------------------------------


def test_login_success_and_logout(client, user):
    response = _post_json(
        client, reverse("api_login"), {"username": "alice", "password": "test1234"}
    )
    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "username": "alice"}
    # La session est ouverte : me le confirme, puis logout la ferme.
    assert client.get(reverse("api_me")).json()["authenticated"] is True
    response = client.post(reverse("api_logout"))
    assert response.json() == {"authenticated": False}
    assert client.get(reverse("api_me")).json()["authenticated"] is False


def test_login_invalid_credentials(client, user):
    response = _post_json(
        client, reverse("api_login"), {"username": "alice", "password": "mauvais"}
    )
    assert response.status_code == 400
    assert client.get(reverse("api_me")).json()["authenticated"] is False


def test_login_empty_body(client):
    assert client.post(reverse("api_login")).status_code == 400


def test_login_rate_limited(client, user, monkeypatch):
    """Même frein anti-force-brute par IP que la page Django.

    Le temps est gelé (`chatbot.ratelimit._now`, point d'injection prévu) :
    sinon les 30 tentatives, lentes à cause du hachage PBKDF2, traversent la
    frontière de la fenêtre de 60 s et le compteur repart à zéro.
    """
    monkeypatch.setattr("chatbot.ratelimit._now", lambda: 1_000_000.0)
    limit = settings.RATE_LIMIT_PER_MINUTE
    for _ in range(limit):
        _post_json(client, reverse("api_login"), {"username": "alice", "password": "x"})
    response = _post_json(
        client, reverse("api_login"), {"username": "alice", "password": "test1234"}
    )
    assert response.status_code == 429
    # Le cache du limiteur est partagé : on le nettoie pour les tests suivants.
    from django.core.cache import cache

    cache.clear()


def test_conversations_send_anonymous_401(client, user):
    """Le endpoint d'envoi renvoie aussi un 401 (et non une redirection)."""
    from chatbot.models import Conversation

    conversation = Conversation.objects.create(user=user, title="t")
    response = client.post(
        reverse("chat_send", args=[conversation.pk]), {"question": "bonjour"}
    )
    assert response.status_code == 401
