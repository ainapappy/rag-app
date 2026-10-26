"""Tests du RateLimiter : fenêtre fixe, 429, réinitialisation, identifiants."""

import pytest
from django.core.cache import cache

from chatbot.ratelimit import RateLimiter


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_allows_up_to_limit_then_blocks():
    limiter = RateLimiter(cache, limit=3, window_seconds=60)
    results = [limiter.hit("cle") for _ in range(4)]
    assert [result.allowed for result in results] == [True, True, True, False]
    assert results[2].remaining == 0
    assert results[3].retry_after > 0


def test_window_reset_after_expiration(monkeypatch):
    """Simule le temps : après la fenêtre, le compteur repart de zéro."""
    fake_time = [1_000_000.0]
    monkeypatch.setattr("chatbot.ratelimit._now", lambda: fake_time[0])
    limiter = RateLimiter(cache, limit=2, window_seconds=10)
    assert limiter.hit("cle").allowed
    assert limiter.hit("cle").allowed
    assert not limiter.hit("cle").allowed
    fake_time[0] += 11  # fenêtre suivante
    result = limiter.hit("cle")
    assert result.allowed
    assert result.remaining == 1


def test_identifiers_have_separate_counters():
    limiter = RateLimiter(cache, limit=1, window_seconds=60)
    assert limiter.hit("alice").allowed
    assert not limiter.hit("alice").allowed
    assert limiter.hit("bob").allowed  # compteur indépendant


def test_invalid_parameters_rejected():
    with pytest.raises(ValueError):
        RateLimiter(cache, limit=0)
    with pytest.raises(ValueError):
        RateLimiter(cache, limit=5, window_seconds=0)


def test_module_now_used_for_time(monkeypatch):
    """Le temps passe bien par le point d'injection `_now`."""
    monkeypatch.setattr("chatbot.ratelimit._now", lambda: 0.0)
    limiter = RateLimiter(cache, limit=1, window_seconds=30)
    result = limiter.hit("cle")
    assert result.retry_after == 30  # int(0.0) % 30 == 0 → fenêtre complète
