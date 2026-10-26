"""Tests de fumée : vérifient que le squelette est en place et chargeable."""

from django.conf import settings

import rag_core  # noqa: F401 — l'import seul suffit pour ce test


def test_rag_core_importable():
    """Le package rag_core s'importe sans erreur (et sans Django)."""
    assert rag_core is not None


def test_language_code_is_french():
    """La configuration Django est bien chargée avec la langue française."""
    assert settings.LANGUAGE_CODE == "fr"


def test_django_settings_load():
    """Le module config.settings se charge sans lever d'exception."""
    from config import settings as django_settings  # noqa: F401
