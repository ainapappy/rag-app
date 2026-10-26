"""Juge de fidélité : un LLM vérifie qu'une réponse est soutenue par le contexte.

⚠️ Mesure INDICATIVE uniquement : le juge est lui-même un LLM, avec ses
propres biais et sa propre tendance à l'indulgence. À croiser avec un
contrôle humain sur un échantillon.
"""

import logging

from rag_core.exceptions import LLMError
from rag_core.models import ChatMessage

logger = logging.getLogger(__name__)

_JUDGE_INSTRUCTIONS = """Tu es un évaluateur de fidélité. On te donne une question,
un CONTEXTE extrait de documents, et une RÉPONSE proposée.

Ta tâche : déterminer si la réponse est ENTIÈREMENT soutenue par le contexte.
Réponds exactement « OUI » si tous les faits de la réponse figurent dans le
contexte, « NON » si la réponse invente, déforme ou dépasse le contexte.
Ne réponds QUE par OUI ou NON."""


class FaithfulnessJudge:
    """Compare réponse et contexte via un appel LLM (OUI/NON strict)."""

    def __init__(self, llm) -> None:
        self._llm = llm

    def is_faithful(self, question: str, context: str, answer: str) -> bool | None:
        """True/False selon le verdict, None si l'appel échoue ou réponse illisible."""
        messages = [
            ChatMessage(role="system", content=_JUDGE_INSTRUCTIONS),
            ChatMessage(
                role="user",
                content=f"Question : {question}\n\nContexte :\n{context}\n\n"
                f"Réponse proposée : {answer}\n\nVerdict (OUI ou NON) :",
            ),
        ]
        try:
            verdict = self._llm.chat(messages)
        except LLMError as exc:
            logger.warning("Juge de fidélité indisponible : %s", exc)
            return None
        cleaned = verdict.strip().upper()
        if cleaned.startswith("OUI"):
            return True
        if cleaned.startswith("NON"):
            return False
        logger.warning("Verdict du juge illisible : %r", verdict)
        return None
