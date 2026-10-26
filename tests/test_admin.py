"""Tests de l'admin : actions, suppression propre, validation des uploads."""

from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from chatbot.models import Document

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client, django_user_model):
    """Client connecté en super-utilisateur."""
    django_user_model.objects.create_superuser("admin", "admin@example.com", "test1234")
    client.force_login(django_user_model.objects.get(username="admin"))
    return client


@pytest.fixture
def document(media_root) -> Document:
    document = Document(title="Doc admin")
    document.file.save("admin.txt", SimpleUploadedFile("admin.txt", b"contenu"), save=True)
    return document


def test_index_action_via_admin_client(admin_client, document, fake_pipeline, patched_container):
    """L'action « Indexer » passe par l'admin et met à jour le statut."""
    url = reverse("admin:chatbot_document_changelist")
    response = admin_client.post(
        url, {"action": "action_index_documents", "_selected_action": [document.pk]}
    )
    assert response.status_code == 302
    document.refresh_from_db()
    assert document.status == Document.Status.INDEXED
    assert document.chunks_count == 3


def test_remove_from_index_action(admin_client, document, fake_pipeline, patched_container):
    document.status = Document.Status.INDEXED
    document.chunks_count = 3
    document.save()
    url = reverse("admin:chatbot_document_changelist")
    response = admin_client.post(
        url, {"action": "action_remove_from_index", "_selected_action": [document.pk]}
    )
    assert response.status_code == 302
    document.refresh_from_db()
    assert document.status == Document.Status.PENDING
    assert document.chunks_count == 0
    assert fake_pipeline.removed == ["admin.txt"]


def test_delete_document_removes_file_and_index(
    admin_client, document, fake_pipeline, patched_container, media_root
):
    file_path = document.file.path
    url = reverse("admin:chatbot_document_delete", args=[document.pk])
    response = admin_client.post(url, {"post": "yes"})  # confirmation
    assert response.status_code == 302
    assert not Document.objects.filter(pk=document.pk).exists()
    assert not Path(file_path).exists()  # fichier physique supprimé
    assert fake_pipeline.removed == ["admin.txt"]  # chunks retirés de l'index


def test_bulk_delete_also_cleans_up(admin_client, document, fake_pipeline, patched_container):
    """La suppression en masse contourne Model.delete() : delete_queryset est là pour ça."""
    file_path = Path(document.file.path)
    url = reverse("admin:chatbot_document_changelist")
    response = admin_client.post(
        url, {"action": "delete_selected", "_selected_action": [document.pk]}, follow=True
    )
    assert response.status_code == 200
    admin_client.post(
        url, {"action": "delete_selected", "_selected_action": [document.pk], "post": "yes"}
    )
    assert not Document.objects.filter(pk=document.pk).exists()
    assert not file_path.exists()
    assert fake_pipeline.removed == ["admin.txt"]


def test_upload_unsupported_extension_refused(admin_client, media_root):
    url = reverse("admin:chatbot_document_add")
    upload = SimpleUploadedFile("malware.exe", b"binaire quelconque")
    response = admin_client.post(url, {"title": "Test", "file": upload})
    assert response.status_code == 200  # formulaire ré-affiché avec erreur
    assert Document.objects.count() == 0
    assert "non pris en charge" in response.content.decode()


def test_upload_too_big_refused(admin_client, media_root, settings):
    settings.MAX_UPLOAD_MB = 1
    url = reverse("admin:chatbot_document_add")
    upload = SimpleUploadedFile("gros.txt", b"x" * (2 * 1024 * 1024))
    response = admin_client.post(url, {"title": "Test", "file": upload})
    assert response.status_code == 200
    assert Document.objects.count() == 0
    assert "trop volumineux" in response.content.decode()


def test_upload_with_index_on_upload_disabled(settings, admin_client, media_root):
    """Avec INDEX_ON_UPLOAD=False, l'upload n'appelle pas le vrai conteneur."""
    settings.INDEX_ON_UPLOAD = False
    url = reverse("admin:chatbot_document_add")
    upload = SimpleUploadedFile("nouveau.txt", b"contenu")
    response = admin_client.post(url, {"title": "Nouveau", "file": upload})
    assert response.status_code == 302
    document = Document.objects.get()
    assert document.status == Document.Status.PENDING
    assert document.original_name == "nouveau.txt"
