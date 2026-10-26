"""Tests de l'API JSON : auth 401, chat 200/422/502, documents, rate limit."""

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

pytestmark = pytest.mark.django_db

CHAT_URL = "/api/chat"
DOCS_URL = "/api/documents"


def _auth_header(raw: str) -> dict:
    return {"HTTP_X_API_KEY": raw}


@pytest.fixture
def api_key():
    from chatbot.models import ApiKey

    return ApiKey.generate("tests")


@pytest.fixture(autouse=True)
def _clear_rate_cache():
    cache.clear()
    yield
    cache.clear()


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------


def test_chat_without_key_is_401(client):
    response = client.post(
        CHAT_URL, '{"question": "bonjour"}', content_type="application/json"
    )
    assert response.status_code == 401


def test_chat_with_wrong_key_is_401(client, api_key):
    response = client.post(
        CHAT_URL,
        '{"question": "bonjour"}',
        content_type="application/json",
        **_auth_header("clé-inventée"),
    )
    assert response.status_code == 401


def test_health_without_auth(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------


def test_chat_ok_with_fake_pipeline(client, api_key, patched_chat_container, rag_pipeline):
    from rag_core.models import Source

    rag_pipeline.sources = (Source(source="doc.txt", page=1, score=0.9, excerpt="extrait"),)
    response = client.post(
        CHAT_URL,
        '{"question": "Combien de jours de congés ?", "history": []}',
        content_type="application/json",
        **_auth_header(api_key[1]),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Réponse de test."
    assert data["found"] is True
    assert data["sources"][0]["source"] == "doc.txt"
    assert set(data.keys()) == {"answer", "found", "sources"}


def test_chat_validates_question_length(client, api_key, patched_chat_container):
    too_long = "x" * 2001
    for body in ('{"question": ""}', f'{{"question": "{too_long}"}}'):
        response = client.post(
            CHAT_URL, body, content_type="application/json", **_auth_header(api_key[1])
        )
        assert response.status_code == 422


def test_chat_history_items_validated(client, api_key, patched_chat_container):
    body = (
        '{"question": "q", "history": [{"role": "chien", "content": "ouaf"}]}'
    )
    response = client.post(
        CHAT_URL, body, content_type="application/json", **_auth_header(api_key[1])
    )
    assert response.status_code == 422


def test_chat_rag_error_is_502_without_leak(client, api_key, patched_chat_container, rag_pipeline):
    from rag_core.exceptions import EmbeddingError

    rag_pipeline.error = EmbeddingError("Impossible de joindre Ollama")
    response = client.post(
        CHAT_URL,
        '{"question": "bonjour"}',
        content_type="application/json",
        **_auth_header(api_key[1]),
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "Impossible de joindre Ollama"
    assert "Traceback" not in response.content.decode()


def test_chat_rate_limited_returns_429(
    client, api_key, patched_chat_container, settings
):
    settings.RATE_LIMIT_PER_MINUTE = 2
    body = '{"question": "bonjour"}'
    for _ in range(2):
        response = client.post(
            CHAT_URL, body, content_type="application/json", **_auth_header(api_key[1])
        )
        assert response.status_code == 200
    blocked = client.post(
        CHAT_URL, body, content_type="application/json", **_auth_header(api_key[1])
    )
    assert blocked.status_code == 429
    assert int(blocked["Retry-After"]) >= 1


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


def test_list_documents_requires_auth(client):
    assert client.get(DOCS_URL).status_code == 401


def test_list_documents_empty(client, api_key):
    response = client.get(DOCS_URL, **_auth_header(api_key[1]))
    assert response.status_code == 200
    assert response.json() == []


def test_upload_and_delete_document(
    client, api_key, patched_container, media_root
):
    upload = client.post(
        DOCS_URL,
        {"title": "Via API", "file": SimpleUploadedFile("doc.pdf", b"%PDF-1.7 contenu")},
        **_auth_header(api_key[1]),
    )
    assert upload.status_code == 201, upload.content
    data = upload.json()
    assert data["title"] == "Via API"
    assert data["status"] == "indexed"
    assert data["chunks_count"] == 3

    listed = client.get(DOCS_URL, **_auth_header(api_key[1]))
    assert len(listed.json()) == 1

    deleted = client.delete(f"{DOCS_URL}/{data['id']}", **_auth_header(api_key[1]))
    assert deleted.status_code == 200
    assert client.get(DOCS_URL, **_auth_header(api_key[1])).json() == []


def test_upload_fake_pdf_refused_422(client, api_key, patched_container):
    upload = client.post(
        DOCS_URL,
        {"title": "Faux", "file": SimpleUploadedFile("faux.pdf", b"PK pas un pdf")},
        **_auth_header(api_key[1]),
    )
    assert upload.status_code == 422
    assert "signature" in upload.json()["detail"]


def test_upload_exe_refused_422(client, api_key, patched_container):
    upload = client.post(
        DOCS_URL,
        {"title": "Exe", "file": SimpleUploadedFile("malware.exe", b"MZ")},
        **_auth_header(api_key[1]),
    )
    assert upload.status_code == 422


def test_api_docs_available(client):
    """La documentation OpenAPI est servie sans authentification."""
    response = client.get("/api/docs")
    assert response.status_code == 200
