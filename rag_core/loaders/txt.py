"""Chargeur de fichiers texte brut (.txt)."""

from pathlib import Path

from rag_core.loaders.base import DocumentLoader
from rag_core.models import Document


class TxtLoader(DocumentLoader):
    """Charge un .txt en un seul Document, sans pagination."""

    supported_extensions = (".txt",)

    def load(self, path: Path, source: str | None = None) -> list[Document]:
        text = self._read_text_with_fallback(path)
        return [Document(source=source or path.name, content=text)]
