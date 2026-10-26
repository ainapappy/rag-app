"""Tests du endpoint /health/ : structure, secrets, deep check staff."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_health_returns_expected_structure(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] is True
    assert isinstance(data["index_chunks"], int)
    assert "embedding_model" in data


def test_health_exposes_no_secrets_or_paths(client):
    response = client.get(reverse("health"))
    content = response.content.decode()
    assert "localhost:11434" not in content
    assert "api_key" not in content.lower().replace("embedding_model", "")
    assert "\\" not in content and "C:" not in content


def test_deep_check_forbidden_for_anonymous(client):
    response = client.get(reverse("health"), {"deep": "1"})
    assert response.status_code == 403


def test_deep_check_forbidden_for_non_staff(client, django_user_model):
    django_user_model.objects.create_user("simple", password="x")
    client.force_login(django_user_model.objects.get(username="simple"))
    assert client.get(reverse("health"), {"deep": "1"}).status_code == 403


def test_deep_check_allowed_for_staff(client, django_user_model, monkeypatch):
    import chatbot.views as views_module

    django_user_model.objects.create_superuser("boss", "b@x.dev", "pwd1234")
    client.force_login(django_user_model.objects.get(username="boss"))
    monkeypatch.setattr(views_module, "ping_llm", lambda timeout_seconds=5.0: "ok")
    response = client.get(reverse("health"), {"deep": "1"})
    assert response.status_code == 200
    assert response.json()["llm"] == "ok"


def test_deep_check_reports_llm_failure_for_staff(client, django_user_model, monkeypatch):
    import chatbot.views as views_module
    from rag_core.exceptions import LLMError

    django_user_model.objects.create_superuser("boss", "b@x.dev", "pwd1234")
    client.force_login(django_user_model.objects.get(username="boss"))

    def fail(timeout_seconds=5.0):
        raise LLMError("LLM injoignable (ConnectError).")

    monkeypatch.setattr(views_module, "ping_llm", fail)
    data = client.get(reverse("health"), {"deep": "1"}).json()
    assert data["status"] == "degraded"
    assert "injoignable" in data["llm"]
