"""Client LLM pour toute API compatible OpenAI (Ollama, OpenAI, vLLM...)."""

import logging
from collections.abc import Iterator

from openai import APIConnectionError, OpenAI, OpenAIError

from rag_core.exceptions import LLMError
from rag_core.llm.base import LLMClient
from rag_core.models import ChatMessage

logger = logging.getLogger(__name__)


class OpenAICompatibleLLM(LLMClient):
    """Client de chat concret, parlant le protocole de l'API OpenAI.

    Le paramètre `client` permet d'injecter un faux client (double de test)
    : c'est le point d'injection qui garantit des tests sans réseau.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        client: object | None = None,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._temperature = temperature
        # Le SDK exige une clé non vide : Ollama accepte n'importe quelle chaîne.
        self._client = client if client is not None else OpenAI(
            base_url=base_url, api_key=api_key
        )

    def chat(self, messages: list[ChatMessage]) -> str:
        """Renvoie le texte de réponse complet du modèle."""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[m.to_dict() for m in messages],
                temperature=self._temperature,
            )
            return response.choices[0].message.content or ""
        except OpenAIError as exc:
            raise self._to_llm_error(exc) from exc

    def stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        """Produit les fragments de réponse au fil de l'eau (générateur)."""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[m.to_dict() for m in messages],
                temperature=self._temperature,
                stream=True,
            )
            for chunk in response:
                # Certains fragments n'ont pas de choix ou un content=None : à ignorer.
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except OpenAIError as exc:
            raise self._to_llm_error(exc) from exc

    def _to_llm_error(self, exc: Exception) -> LLMError:
        """Convertit une erreur du SDK en LLMError avec un message clair.

        Attention : ne jamais inclure la clé API dans le message ni les logs.
        """
        if isinstance(exc, APIConnectionError):
            message = (
                f"Impossible de joindre le LLM à {self._base_url} : "
                f"vérifiez qu'Ollama est lancé. ({exc})"
            )
        else:
            message = f"Erreur du LLM (modèle {self._model!r}) : {exc}"
        logger.error(message)
        return LLMError(message)
