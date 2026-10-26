"""Interface abstraite des chargeurs de documents (≈ interface PHP)."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from rag_core.exceptions import LoaderError
from rag_core.models import Document

logger = logging.getLogger(__name__)


class DocumentLoader(ABC):
    """Contrat commun à tous les chargeurs de fichiers.

    Chaque classe concrète déclare ses extensions via l'attribut de classe
    `supported_extensions` (≈ const de classe PHP).
    """

    supported_extensions: tuple[str, ...] = ()

    @abstractmethod
    def load(self, path: Path, source: str | None = None) -> list[Document]:
        """Charge un fichier et renvoie la liste des Documents (une entrée par page)."""

    def _read_text_with_fallback(self, path: Path) -> str:
        """Lit un fichier texte en UTF-8, avec repli sur latin-1 si échec."""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning(
                "Fichier %s : décodage UTF-8 impossible, repli sur latin-1.", path.name
            )
            return path.read_text(encoding="latin-1")
        except OSError as exc:
            raise LoaderError(f"Impossible de lire {path.name} : {exc}") from exc
