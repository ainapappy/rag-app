"""Embeddings pour toute API compatible OpenAI (Ollama, OpenAI...)."""

import logging

from openai import APIConnectionError, OpenAI, OpenAIError

from rag_core.embeddings.base import EmbeddingProvider
from rag_core.exceptions import EmbeddingError

logger = logging.getLogger(__name__)


class OpenAICompatibleEmbeddings(EmbeddingProvider):
    """Fournisseur d'embeddings concret, par lots (batching).

    Le paramètre `client` permet d'injecter un faux client en test.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        batch_size: int = 32,
        client: object | None = None,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._batch_size = batch_size
        self._client = client if client is not None else OpenAI(
            base_url=base_url, api_key=api_key
        )

    @property
    def model_name(self) -> str:
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Calcule les vecteurs par lots de `batch_size` textes."""
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            try:
                response = self._client.embeddings.create(model=self._model, input=batch)
            except OpenAIError as exc:
                raise self._to_embedding_error(exc) from exc
            batch_vectors = [item.embedding for item in response.data]
            if len(batch_vectors) != len(batch):
                raise EmbeddingError(
                    f"L'API a renvoyé {len(batch_vectors)} vecteurs pour "
                    f"{len(batch)} textes (modèle {self._model!r})."
                )
            vectors.extend(batch_vectors)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def _to_embedding_error(self, exc: Exception) -> EmbeddingError:
        """Convertit une erreur du SDK en EmbeddingError clair (sans la clé API)."""
        if isinstance(exc, APIConnectionError):
            message = (
                f"Impossible de joindre le service d'embeddings à {self._base_url} : "
                f"vérifiez qu'Ollama est lancé. ({exc})"
            )
        else:
            message = f"Erreur d'embeddings (modèle {self._model!r}) : {exc}"
        logger.error(message)
        return EmbeddingError(message)
