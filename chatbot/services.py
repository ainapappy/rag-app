"""Services métier de l'application chatbot (couche fine par-dessus rag_core).

Aucune logique d'indexation ici non plus : ces services orchestrent
rag_core et mettent à jour les modèles Django.
"""

from pathlib import Path

from django.utils import timezone

from chatbot.models import Document
from rag_core.container import Container, get_container
from rag_core.exceptions import RagError


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
