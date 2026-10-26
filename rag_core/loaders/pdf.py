"""Chargeur de fichiers PDF (.pdf) via pypdf : un Document par page."""

import logging
from pathlib import Path

from rag_core.exceptions import LoaderError
from rag_core.loaders.base import DocumentLoader
from rag_core.models import Document

logger = logging.getLogger(__name__)


class PdfLoader(DocumentLoader):
    """Extrait le texte page par page (pages numérotées à partir de 1).

    Les pages vides sont ignorées. Un PDF sans texte extractible (scanné)
    ou corrompu lève une `LoaderError` avec un message explicite.
    """

    supported_extensions = (".pdf",)

    def load(self, path: Path, source: str | None = None) -> list[Document]:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
        except LoaderError:
            raise
        except Exception as exc:
            raise LoaderError(f"PDF illisible ou corrompu : {path.name} ({exc})") from exc

        documents: list[Document] = []
        for number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:  # page mal formée : on l'ignore avec un avertissement
                logger.warning("Page %d de %s illisible : %s", number, path.name, exc)
                continue
            # Normalisation des espaces : l'extraction PDF colle parfois les mots.
            text = " ".join(text.split())
            if not text:
                continue
            documents.append(
                Document(source=source or path.name, content=text, page=number)
            )

        if not documents:
            raise LoaderError(
                f"Aucun texte extractible dans {path.name} : le PDF est probablement "
                "scanné (images). L'OCR n'est pas pris en charge."
            )
        return documents
