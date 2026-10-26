"""Tests des réglages de production : cookies sécurisés, hôtes depuis l'env."""

import importlib


def test_debug_false_activates_secure_settings(monkeypatch):
    """Avec DJANGO_DEBUG=False : HSTS, cookies sécurisés, hôtes pris dans l'env."""
    monkeypatch.setenv("DJANGO_DEBUG", "False")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "exemple.com")
    import config.settings as config_settings

    importlib.reload(config_settings)
    try:
        assert config_settings.DEBUG is False
        assert config_settings.SESSION_COOKIE_SECURE is True
        assert config_settings.CSRF_COOKIE_SECURE is True
        assert config_settings.SECURE_HSTS_SECONDS > 0
        assert config_settings.SECURE_REFERRER_POLICY == "same-origin"
        assert "exemple.com" in config_settings.ALLOWED_HOSTS
    finally:
        monkeypatch.delenv("DJANGO_DEBUG", raising=False)
        monkeypatch.delenv("DJANGO_ALLOWED_HOSTS", raising=False)
        importlib.reload(config_settings)  # restaure l'état développement
        # importlib.reload ne vide PAS le namespace : retirer les attributs
        # qui n'existent qu'en production pour ne pas polluer la suite.
        for attribute in (
            "SESSION_COOKIE_SECURE",
            "CSRF_COOKIE_SECURE",
            "SECURE_HSTS_SECONDS",
            "SECURE_REFERRER_POLICY",
        ):
            config_settings.__dict__.pop(attribute, None)


def test_debug_mode_keeps_cookies_usable_locally():
    """En développement (état normal du module), pas de cookie forcé sécurisé."""
    import config.settings as config_settings

    assert config_settings.DEBUG is True
    assert getattr(config_settings, "SESSION_COOKIE_SECURE", False) is False
