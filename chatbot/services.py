"""Services métier de l'application chatbot (couche fine par-dessus rag_core).

Aucune logique RAG ici non plus : ces services orchestrent rag_core
et mettent à jour les modèles Django.
"""

import json
import logging
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path

from django.utils import timezone

from chatbot.models import Conversation, Document, Message
from rag_core.container import Container, get_container
from rag_core.exceptions import RagError
from rag_core.models import ChatMessage
from rag_core.pipeline.rag import NO_ANSWER_MESSAGE

logger = logging.getLogger(__name__)


class DocumentIndexingService:
    """Gère le cycle de vie d'indexation d'un `Document`.

    En cas d'échec du pipeline, le document passe en `error` avec le
    message : l'admin ne plante jamais pour une erreur métier.
    """

    def __init__(self, container: Container | None = None) -> None:
        self._container = container if container is not None else get_container()

    def index(self, document: Document) -> None:
        """Indexe (ou réindexe) un document et met à jour son statut."""
        document.status = Document.Status.INDEXING
        document.error_message = ""
        document.save(update_fields=["status", "error_message"])

        try:
            report = self._container.ingestion_pipeline.ingest_file(
                Path(document.file.path),
                source=document.original_name,
                force=True,
            )
        except (RagError, OSError) as exc:
            document.status = Document.Status.ERROR
            document.error_message = str(exc)
            document.save(update_fields=["status", "error_message"])
            return

        document.status = Document.Status.INDEXED
        document.chunks_count = report.chunks_count
        document.indexed_at = timezone.now()
        document.error_message = ""
        document.save(
            update_fields=["status", "chunks_count", "indexed_at", "error_message"]
        )

    def remove_from_index(self, document: Document) -> None:
        """Retire les chunks du document de l'index et repasse en attente."""
        self._container.ingestion_pipeline.remove_source(document.original_name)
        document.status = Document.Status.PENDING
        document.chunks_count = 0
        document.indexed_at = None
        document.save(update_fields=["status", "chunks_count", "indexed_at"])

    def purge(self, document: Document) -> None:
        """Retire les chunks de l'index et le fichier du disque (sans supprimer la ligne).

        Utilisé par l'admin ET l'API avant la suppression du modèle.
        """
        self.remove_from_index(document)
        document.file.delete(save=False)


class ApiChatService:
    """Chat sans conversation persistée, pour l'API JSON (≈ ChatService minimal)."""

    def __init__(self, container: Container | None = None) -> None:
        self._container = container if container is not None else get_container()

    def ask(self, question: str, history: tuple[ChatMessage, ...] = ()):
        """Délègue au pipeline RAG et renvoie l'`Answer` (sans persistance)."""
        return self._container.rag_pipeline.ask(question, history=history)


class ChatService:
    """Conversations persistantes : historique fenêtré, réponses, streaming SSE.

    Limite documentée : le streaming occupe un worker WSGI pendant toute la
    génération (d'où `STREAMING_ENABLED` pour le désactiver en production).
    """

    TITLE_MAX_CHARS = 60

    def __init__(self, container: Container | None = None) -> None:
        self._container = container if container is not None else get_container()

    def history(self, conversation: Conversation) -> list[ChatMessage]:
        """Les `HISTORY_WINDOW` derniers messages, en ordre chronologique."""
        window = self._container.settings.history_window
        messages = list(conversation.messages.all())[-window:]
        return [ChatMessage(role=message.role, content=message.content) for message in messages]

    def ask(self, conversation: Conversation, question: str) -> Message:
        """Enregistre la question, répond, enregistre et renvoie la réponse."""
        history = self.history(conversation)
        self._save_user_message(conversation, question)
        answer = self._container.rag_pipeline.ask(question, history=tuple(history))
        return Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=answer.text,
            sources=[asdict(source) for source in answer.sources],
        )

    def stream(self, conversation: Conversation, question: str) -> Iterator[str]:
        """Générateur d'événements SSE (chaînes déjà formatées).

        Le message assistant est enregistré dans un bloc `finally` : même si
        le client coupe, le texte partiel est conservé.
        """
        history = self.history(conversation)
        self._save_user_message(conversation, question)

        def generate():
            parts: list[str] = []
            sources_payload: list[dict] = []
            try:
                streamed = self._container.rag_pipeline.ask_stream(
                    question, history=tuple(history)
                )
                sources_payload = [asdict(source) for source in streamed.sources]
                yield _sse("sources", json.dumps(sources_payload, ensure_ascii=False))
                if not streamed.found:
                    parts.append(NO_ANSWER_MESSAGE)
                    yield _sse("token", json.dumps({"t": NO_ANSWER_MESSAGE}, ensure_ascii=False))
                else:
                    for token in streamed.tokens:
                        parts.append(token)
                        yield _sse("token", json.dumps({"t": token}, ensure_ascii=False))
            except RagError as exc:
                logger.error("Erreur RAG pendant le chat : %s", exc)
                yield _sse("error", json.dumps({"message": str(exc)}, ensure_ascii=False))
            finally:
                assistant = Message.objects.create(
                    conversation=conversation,
                    role="assistant",
                    content="".join(parts),
                    sources=sources_payload,
                )
                yield _sse("done", json.dumps({"id": assistant.pk}))

        return generate()

    # -- Internes -----------------------------------------------------------------

    def _save_user_message(self, conversation: Conversation, question: str) -> None:
        Message.objects.create(conversation=conversation, role="user", content=question)
        if not conversation.title:
            conversation.title = question[: self.TITLE_MAX_CHARS]
            conversation.save(update_fields=["title"])


def _sse(event: str, data: str) -> str:
    """Formate un événement SSE complet (`event:` + `data:` + ligne vide)."""
    return f"event: {event}\ndata: {data}\n\n"
