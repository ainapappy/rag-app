"""Faux client LLM pour les tests : aucun réseau, réponses programmées."""

from collections.abc import Iterator

from rag_core.llm.base import LLMClient
from rag_core.models import ChatMessage

DEFAULT_RESPONSE = "Réponse par défaut du faux LLM."


class FakeLLM(LLMClient):
    """Double de test qui enregistre les appels et renvoie des réponses fixes.

    Permet de tester les pipelines sans Ollama ni Internet : on programme
    les réponses attendues, puis on inspecte `calls` (≈ Mock de PHPUnit).
    """

    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: list[list[ChatMessage]] = []

    def chat(self, messages: list[ChatMessage]) -> str:
        self.calls.append(messages)
        if self.responses:
            return self.responses.pop(0)
        return DEFAULT_RESPONSE

    def stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        text = self.chat(messages)
        # Découpe en petits fragments pour simuler l'arrivée token par token.
        for i in range(0, len(text), 8):
            yield text[i : i + 8]
