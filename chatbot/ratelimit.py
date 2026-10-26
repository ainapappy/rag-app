"""Limitation de débit à fenêtre fixe, basée sur le cache Django.

⚠️ Limite documentée : avec `LocMemCache` (défaut), les compteurs sont
**par processus** : en production multi-processus, la limite réelle est
multipliée par le nombre de workers. Prévoir un cache partagé — par exemple :

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_table",  # puis : python manage.py createcachetable
    }
}
```
(ou un cache Redis/Memcached). Le code de `RateLimiter` reste identique.
"""

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitResult:
    """Résultat d'un « coup » : autorisé, quota restant, délai d'attente."""

    allowed: bool
    remaining: int
    retry_after: int


def _now() -> float:
    """Point d'injection du temps (tests : monkeypatch cette fonction)."""
    return time.time()


class RateLimiter:
    """Compteur par fenêtre fixe dans le cache Django.

    La clé intègre le numéro de fenêtre : elle expire naturellement
    (`timeout = window_seconds`), ce qui réinitialise le compteur.
    """

    def __init__(self, cache, limit: int, window_seconds: int = 60) -> None:
        if limit <= 0:
            raise ValueError(f"limit doit être > 0 (reçu : {limit})")
        if window_seconds <= 0:
            raise ValueError(f"window_seconds doit être > 0 (reçu : {window_seconds})")
        self._cache = cache
        self._limit = limit
        self._window = window_seconds

    def hit(self, identifier: str) -> RateLimitResult:
        """Compte une requête pour `identifier` et renvoie le verdict."""
        now = _now()
        key = f"ratelimit:{identifier}:{int(now) // self._window}"
        # `add` est atomique : initialise à 0 si la clé n'existe pas encore.
        self._cache.add(key, 0, timeout=self._window)
        count = self._cache.get(key, 0) + 1
        self._cache.set(key, count, timeout=self._window)
        retry_after = self._window - (int(now) % self._window)
        return RateLimitResult(
            allowed=count <= self._limit,
            remaining=max(self._limit - count, 0),
            retry_after=max(retry_after, 1),
        )


def default_limiter() -> RateLimiter:
    """Limiter par défaut de l'application (RATE_LIMIT_PER_MINUTE du .env)."""
    from django.conf import settings
    from django.core.cache import cache

    return RateLimiter(
        cache,
        limit=getattr(settings, "RATE_LIMIT_PER_MINUTE", 30),
        window_seconds=60,
    )
