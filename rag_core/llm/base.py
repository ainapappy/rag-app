"""Interface abstraite d'un client LLM (≈ interface PHP)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from rag_core.models import ChatMessage


class LLMClient(ABC):
    """Contrat commun à tous les clients de chat.

    Une classe qui n'implémente pas `chat` et `stream` ne peut pas être
    instanciée — même mécanique qu'une interface PHP non implémentée.
    """

    @abstractmethod
    def chat(self, messages: list[ChatMessage]) -> str:
        """Envoie la conversation et renvoie le texte de réponse complet."""

    @abstractmethod
    def stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        """Envoie la conversation et produit la réponse fragment par fragment."""
