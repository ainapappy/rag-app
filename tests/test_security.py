"""Tests du frein sur le login et du filtre de secrets dans les logs."""

import logging

import pytest
from django.core.cache import cache
from django.urls import reverse

from config.settings import SecretMaskingFilter

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_login_throttled_by_ip(client, settings, django_user_model):
    """Après RATE_LIMIT_PER_MINUTE tentatives, le login renvoie 429."""
    settings.RATE_LIMIT_PER_MINUTE = 2
    django_user_model.objects.create_user("marcel", password="mot-de-passe")
    url = reverse("login")
    for _ in range(2):
        response = client.post(
            url, {"username": "marcel", "password": "mauvais-mot-de-passe"}
        )
        assert response.status_code == 200  # formulaire re-affiché (identifiants faux)
    blocked = client.post(url, {"username": "marcel", "password": "mot-de-passe"})
    assert blocked.status_code == 429
    assert int(blocked["Retry-After"]) >= 1


def test_successful_login_not_blocked_below_limit(client, settings, django_user_model):
    settings.RATE_LIMIT_PER_MINUTE = 3
    django_user_model.objects.create_user("lea", password="correct")
    url = reverse("login")
    response = client.post(url, {"username": "lea", "password": "correct"})
    assert response.status_code == 302  # connectée


def test_secret_masking_filter_masks_api_keys():
    filt = SecretMaskingFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="Requête avec X-API-Key: sk-secret-123 et Authorization: Bearer abc.def",
        args=(), exc_info=None,
    )
    assert filt.filter(record) is True
    message = record.getMessage()
    assert "sk-secret-123" not in message
    assert "abc.def" not in message
    assert "X-API-Key: ***" in message


def test_secret_masking_filter_keeps_normal_logs():
    filt = SecretMaskingFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="guide_rag.md : 6 chunks indexés.",
        args=(), exc_info=None,
    )
    assert filt.filter(record) is True
    assert record.getMessage() == "guide_rag.md : 6 chunks indexés."
