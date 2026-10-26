"""Tests du modèle Document : original_name auto, unicité, statut par défaut."""

import pytest
from django.core.files.base import ContentFile
from django.db import IntegrityError

from chatbot.models import Document

pytestmark = pytest.mark.django_db


def _create_document(name: str = "rapport.txt", title: str = "Rapport") -> Document:
    document = Document(title=title)
    document.file.save(name, ContentFile(b"contenu de test"), save=True)
    return document


def test_original_name_filled_automatically(media_root):
    document = _create_document("rapport.txt")
    assert document.original_name == "rapport.txt"
    assert document.pk is not None


def test_default_status_is_pending(media_root):
    document = _create_document()
    assert document.status == Document.Status.PENDING
    assert document.chunks_count == 0
    assert document.indexed_at is None
    assert str(document) == document.title


def test_original_name_is_unique(media_root):
    """La contrainte d'unicité en base empêche deux sources identiques."""
    Document.objects.create(title="Premier", file="documents/a.txt", original_name="a.txt")
    with pytest.raises(IntegrityError):
        Document.objects.create(title="Second", file="documents/b.txt", original_name="a.txt")


def test_ordering_most_recent_first(media_root):
    first = _create_document("a.txt", title="A")
    second = _create_document("b.txt", title="B")
    assert list(Document.objects.all()) == [second, first]
