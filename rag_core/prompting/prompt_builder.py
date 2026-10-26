"""Construction du prompt RAG : instructions strictes + contexte numéroté."""

from rag_core.models import ChatMessage, SearchResult

# Instructions système : le modèle ne répond qu'à partir du contexte fourni.
SYSTEM_INSTRUCTIONS = """Tu es un assistant documentaire. Réponds à la question de
l'utilisateur en t'appuyant UNIQUEMENT sur les documents fournis ci-dessous.

Règles :
- Si l'information ne figure pas dans les documents, réponds exactement que tu
  ne l'as pas trouvée dans les documents ; n'utilise jamais tes propres connaissances.
- Cite tes sources avec les numéros entre crochets, par exemple [1] ou [2].
- N'invente jamais de faits, de chiffres ni de citations.
- Réponds dans la langue de la question."""

# Taille maximale du contexte (caractères) : au-delà, on tronque les chunks
# les moins bien classés pour ne pas dépasser la fenêtre du petit modèle local.
MAX_CONTEXT_CHARS = 6000


class PromptBuilder:
    """Assemble messages système, historique, contexte et question.

    Ordre des messages : système → historique → question + contexte.
    """

    def __init__(self, max_context_chars: int = MAX_CONTEXT_CHARS) -> None:
        self._max_context_chars = max_context_chars

    def build(
        self,
        question: str,
        results: list[SearchResult],
        history: tuple[ChatMessage, ...] = (),
    ) -> list[ChatMessage]:
        """Construit la liste de messages pour le LLM."""
        context = self._format_context(results)
        messages: list[ChatMessage] = [ChatMessage(role="system", content=SYSTEM_INSTRUCTIONS)]
        # Historique des tours précédents, avant la question finale.
        messages.extend(history)
        messages.append(
            ChatMessage(
                role="user",
                content=f"Documents pertinents :\n\n{context}\n\nQuestion : {question}",
            )
        )
        return messages

    def _format_context(self, results: list[SearchResult]) -> str:
        """Formate les chunks : [n] (fichier, page N)\n<texte>, avec troncature."""
        parts: list[str] = []
        used = 0
        for number, result in enumerate(results, start=1):
            chunk = result.chunk
            page = f", page {chunk.page}" if chunk.page is not None else ""
            header = f"[{number}] ({chunk.source}{page})"
            remaining = self._max_context_chars - used - len(header) - 2
            if remaining <= 0:
                break  # plus de place : les chunks suivants sont abandonnés
            text = chunk.text
            if len(text) > remaining:
                text = text[:remaining] + "…"
            parts.append(f"{header}\n{text}")
            used += len(header) + len(text) + 2
        return "\n\n".join(parts) if parts else "(aucun document fourni)"
