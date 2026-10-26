"""Tests du modèle ApiKey : génération, authentification, activation."""

import hashlib

import pytest
from django.utils import timezone

from chatbot.models import ApiKey

pytestmark = pytest.mark.django_db


def test_generate_returns_raw_key_once():
    api_key, raw = ApiKey.generate("integration")
    assert raw and len(raw) >= 32
    assert api_key.prefix == raw[:8]
    # Le hash stocké n'est pas la clé, mais bien le sha256 de la clé.
    assert api_key.key_hash != raw
    assert api_key.key_hash == hashlib.sha256(raw.encode()).hexdigest()


def test_generate_keys_are_unique():
    _, first = ApiKey.generate("a")
    _, second = ApiKey.generate("b")
    assert first != second


def test_authenticate_valid_key_updates_last_used():
    api_key, raw = ApiKey.generate("test")
    assert api_key.last_used_at is None
    found = ApiKey.authenticate(raw)
    assert found is not None
    assert found.pk == api_key.pk
    assert found.last_used_at is not None
    assert found.last_used_at <= timezone.now()


def test_authenticate_invalid_key_returns_none():
    ApiKey.generate("test")
    assert ApiKey.authenticate("mauvaise-cle") is None
    assert ApiKey.authenticate("") is None


def test_authenticate_inactive_key_returns_none():
    api_key, raw = ApiKey.generate("révoquée")
    api_key.is_active = False
    api_key.save(update_fields=["is_active"])
    assert ApiKey.authenticate(raw) is None
