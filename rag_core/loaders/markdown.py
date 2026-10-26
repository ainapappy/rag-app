"""Chargeur de fichiers Markdown (.md) : texte brut + titre extrait."""

import re
from pathlib import Path

from rag_core.loaders.base import DocumentLoader
from rag_core.models import Document

# Premier titre de niveau 1 (« # Titre ») en début de ligne.
_TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)


class MarkdownLoader(DocumentLoader):
    """Charge un .md en conservant le texte brut ; extrait le titre du document."""

    supported_extensions = (".md",)

    def load(self, path: Path, source: str | None = None) -> list[Document]:
        text = self._read_text_with_fallback(path)
        metadata: dict[str, str] = {}
        match = _TITLE_PATTERN.search(text)
        if match:
            metadata["title"] = match.group(1).strip()
        return [Document(source=source or path.name, content=text, metadata=metadata)]
