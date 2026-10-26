"""Configuration typée du cœur RAG (pydantic-settings, ≈ config() de Laravel).

Les valeurs proviennent des variables d'environnement / du fichier `.env`,
avec les défauts du contrat d'architecture. Django côté `config/settings.py`,
métier côté `rag_core.settings` : les deux mondes lisent le même `.env`.
"""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from rag_core.exceptions import ConfigError

VECTOR_STORE_CHOICES = {"simple", "chroma"}
CHUNKER_STRATEGY_CHOICES = {"fixed", "paragraph"}
RETRIEVER_CHOICES = {"vector", "hybrid"}


class Settings(BaseSettings):
    """Tous les réglages du cœur RAG, validés au chargement.

    `extra="ignore"` : le `.env` contient aussi des variables `DJANGO_*`
    destinées à Django ; elles sont ignorées ici sans erreur.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM (API compatible OpenAI) ----------------------------------------
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "llama3.2:3b"
    llm_temperature: float = 0.2

    # --- Embeddings -----------------------------------------------------------
    embed_base_url: str = "http://localhost:11434/v1"
    embed_api_key: str = "ollama"
    embed_model: str = "nomic-embed-text"
    embed_batch_size: int = Field(default=32, gt=0)

    # --- Vector store ---------------------------------------------------------
    vector_store: str = "simple"
    vector_store_path: str = "data/index"

    # --- Chunking -------------------------------------------------------------
    chunker_strategy: str = "fixed"
    chunk_size: int = Field(default=700, gt=0)
    chunk_overlap: int = Field(default=100, ge=0)

    # --- Recherche / RAG --------------------------------------------------------
    top_k: int = Field(default=4, gt=0)
    min_score: float = 0.35
    history_window: int = Field(default=6, ge=0)
    streaming_enabled: bool = True
    retriever: str = "vector"

    # --- Ingestion / uploads ------------------------------------------------------
    index_on_upload: bool = True
    max_upload_mb: int = Field(default=10, gt=0)

    # --- Divers ---------------------------------------------------------------------
    rate_limit_per_minute: int = Field(default=30, gt=0)

    @model_validator(mode="after")
    def _validate_coherence(self) -> "Settings":
        """Valide la cohérence des valeurs entre elles (≈ FormRequest::rules)."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"CHUNK_OVERLAP ({self.chunk_overlap}) doit être strictement "
                f"inférieur à CHUNK_SIZE ({self.chunk_size})"
            )
        if not 0 <= self.min_score <= 1:
            raise ValueError(f"MIN_SCORE ({self.min_score}) doit être compris entre 0 et 1")
        if self.vector_store not in VECTOR_STORE_CHOICES:
            raise ValueError(
                f"VECTOR_STORE doit être parmi {sorted(VECTOR_STORE_CHOICES)}, "
                f"reçu : {self.vector_store!r}"
            )
        if self.chunker_strategy not in CHUNKER_STRATEGY_CHOICES:
            raise ValueError(
                f"CHUNKER_STRATEGY doit être parmi {sorted(CHUNKER_STRATEGY_CHOICES)}, "
                f"reçu : {self.chunker_strategy!r}"
            )
        if self.retriever not in RETRIEVER_CHOICES:
            raise ValueError(
                f"RETRIEVER doit être parmi {sorted(RETRIEVER_CHOICES)}, "
                f"reçu : {self.retriever!r}"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance unique de Settings (singleton léger via cache).

    Lève une `ConfigError` (et non l'erreur pydantic brute) pour que
    l'appelant n'ait qu'une seule exception métier à attraper.
    """
    try:
        return Settings()
    except ValueError as exc:
        raise ConfigError(f"Configuration invalide : {exc}") from exc
