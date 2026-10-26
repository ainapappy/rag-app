"""Tests du DocumentIndexingService (conteneur factice, aucun réseau)."""

import pytest
from django.core.files.base import ContentFile

from chatbot.models import Document

pytestmark = pytest.mark.django_db


def _create_document(media_root, name="doc.txt") -> Document:
    document = Document(title="Doc de test")
    document.file.save(name, ContentFile(b"contenu"), save=True)
    return document


def test_index_success_updates_status(indexing_service, fake_pipeline, media_root):
    document = _create_document(media_root)
    indexing_service.index(document)
    document.refresh_from_db()
    assert document.status == Document.Status.INDEXED
    assert document.chunks_count == 3
    assert document.indexed_at is not None
    assert document.error_message == ""
    # Le pipeline a bien été appelé avec la source et force=True.
    path, source, force = fake_pipeline.calls[0]
    assert source == "doc.txt"
    assert force is True
    assert path.endswith("doc.txt")


def test_index_error_sets_error_status(indexing_service, fake_pipeline, media_root):
    from rag_core.exceptions import EmbeddingError

    fake_pipeline.error = EmbeddingError("LLM injoignable")
    document = _create_document(media_root)
    indexing_service.index(document)  # ne lève pas
    document.refresh_from_db()
    assert document.status == Document.Status.ERROR
    assert "LLM injoignable" in document.error_message
    assert document.chunks_count == 0


def test_remove_from_index(indexing_service, fake_pipeline, media_root):
    document = _create_document(media_root)
    indexing_service.index(document)
    indexing_service.remove_from_index(document)
    document.refresh_from_db()
    assert document.status == Document.Status.PENDING
    assert document.chunks_count == 0
    assert document.indexed_at is None
    assert fake_pipeline.removed == ["doc.txt"]


def test_reindex_after_error(indexing_service, fake_pipeline, media_root):
    from rag_core.exceptions import EmbeddingError

    document = _create_document(media_root)
    fake_pipeline.error = EmbeddingError("panne")
    indexing_service.index(document)
    fake_pipeline.error = None
    indexing_service.index(document)
    document.refresh_from_db()
    assert document.status == Document.Status.INDEXED
    assert document.error_message == ""
