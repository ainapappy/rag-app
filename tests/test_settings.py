"""Tests de la configuration typée `rag_core.settings` (sans fichier ni réseau)."""

import pytest
from pydantic import ValidationError

from rag_core.exceptions import ConfigError
from rag_core.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Vide le cache de get_settings() avant/après chaque test (isolation)."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_default_values():
    """Les défauts du contrat sont présents quand aucune variable n'écrase."""
    settings = Settings(_env_file=None)
    assert settings.llm_base_url == "http://localhost:11434/v1"
    assert settings.llm_api_key == "ollama"
    assert settings.llm_model == "llama3.2:3b"
    assert settings.llm_temperature == 0.2
    assert settings.embed_base_url == "http://localhost:11434/v1"
    assert settings.embed_model == "nomic-embed-text"
    assert settings.embed_batch_size == 32
    assert settings.vector_store == "simple"
    assert settings.vector_store_path == "data/index"
    assert settings.chunker_strategy == "fixed"
    assert settings.chunk_size == 700
    assert settings.chunk_overlap == 100
    assert settings.top_k == 4
    assert settings.min_score == 0.35
    assert settings.history_window == 6
    assert settings.streaming_enabled is True
    assert settings.retriever == "vector"
    assert settings.index_on_upload is True
    assert settings.max_upload_mb == 10
    assert settings.rate_limit_per_minute == 30


def test_env_override(monkeypatch):
    """Les variables d'environnement écrasent les défauts (casting typé)."""
    monkeypatch.setenv("LLM_MODEL", "mistral")
    monkeypatch.setenv("TOP_K", "7")
    monkeypatch.setenv("STREAMING_ENABLED", "false")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.7")
    settings = Settings(_env_file=None)
    assert settings.llm_model == "mistral"
    assert settings.top_k == 7
    assert settings.streaming_enabled is False
    assert settings.llm_temperature == 0.7


def test_chunk_overlap_must_be_smaller_than_chunk_size(monkeypatch):
    """Erreur si CHUNK_OVERLAP >= CHUNK_SIZE."""
    monkeypatch.setenv("CHUNK_SIZE", "100")
    monkeypatch.setenv("CHUNK_OVERLAP", "100")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_min_score_bounds(monkeypatch):
    """MIN_SCORE doit rester dans [0, 1]."""
    monkeypatch.setenv("MIN_SCORE", "1.5")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_vector_store(monkeypatch):
    """VECTOR_STORE n'accepte que « simple » ou « chroma »."""
    monkeypatch.setenv("VECTOR_STORE", "redis")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_django_vars_are_ignored(monkeypatch):
    """Les variables DJANGO_* présentes dans l'environnement ne cassent rien."""
    monkeypatch.setenv("DJANGO_SECRET_KEY", "ignored-here")
    monkeypatch.setenv("DJANGO_DEBUG", "True")
    Settings(_env_file=None)  # ne lève pas


def test_get_settings_returns_same_instance():
    """get_settings() est mis en cache : même objet à chaque appel."""
    assert get_settings() is get_settings()


def test_get_settings_raises_config_error(monkeypatch):
    """Une config incohérente lève la ConfigError métier (pas l'erreur pydantic)."""
    monkeypatch.setenv("CHUNK_SIZE", "50")
    monkeypatch.setenv("CHUNK_OVERLAP", "60")
    with pytest.raises(ConfigError):
        get_settings()
