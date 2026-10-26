"""Reformulation des questions de suivi en questions autonomes.

Exemple : après « Combien de jours de congés ? », la question « et pour les
congés maladie ? » devient « Quelle est la politique de congés maladie ? » —
indispensable pour que la recherche vectorielle retrouve le bon passage.
"""

import logging

from rag_core.exceptions import LLMError
from rag_core.models import ChatMessage

logger = logging.getLogger(__name__)

_REWRITE_INSTRUCTIONS = """Tu es un moteur de reformulation. À partir de l'échange
précédent, reformule la DERNIÈRE question de l'utilisateur en une question
autonome, compréhensible sans contexte (remplace les pronoms et ellipses).

Règles :
- Une seule phrase, sans introduction ni commentaire.
- Dans la langue de la question.
- Ne réponds JAMAIS à la question : reformule-la seulement."""


class QueryRewriter:
    """Reformule une question à partir de l'historique (1 appel LLM maximum)."""

    def __init__(self, llm) -> None:
        self._llm = llm

    def rewrite(self, question: str, history: tuple[ChatMessage, ...] = ()) -> str:
        """Renvoie la question autonome ; repli sur l'originale en cas d'erreur."""
        if not history:
            return question  # rien à reformuler : zéro appel LLM
        messages = [ChatMessage(role="system", content=_REWRITE_INSTRUCTIONS)]
        for message in history:
            prefix = "Utilisateur" if message.role == "user" else "Assistant"
            messages.append(ChatMessage(role="user", content=f"{prefix} : {message.content}"))
        messages.append(
            ChatMessage(role="user", content=f"Question à reformuler : {question}")
        )
        try:
            rewritten = self._llm.chat(messages)
        except LLMError as exc:
            logger.warning("Reformulation impossible, question originale conservée : %s", exc)
            return question
        cleaned = rewritten.strip().strip('"').strip()
        return cleaned or question
