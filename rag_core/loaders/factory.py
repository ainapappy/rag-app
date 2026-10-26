"""Factory des chargeurs : choisit le loader selon l'extension du fichier."""

from pathlib import Path

from rag_core.exceptions import UnsupportedFileTypeError
from rag_core.loaders.base import DocumentLoader
from rag_core.loaders.markdown import MarkdownLoader
from rag_core.loaders.pdf import PdfLoader
from rag_core.loaders.txt import TxtLoader

_LOADER_TYPES: tuple[type[DocumentLoader], ...] = (TxtLoader, MarkdownLoader, PdfLoader)


class LoaderFactory:
    """Agrège les loaders disponibles et sélectionne celui du bon type."""

    @staticmethod
    def supported_extensions() -> tuple[str, ...]:
        """Toutes les extensions prises en charge, triées."""
        extensions: set[str] = set()
        for loader_type in _LOADER_TYPES:
            extensions.update(loader_type.supported_extensions)
        return tuple(sorted(extensions))

    @staticmethod
    def supports(path: Path) -> bool:
        """True si l'extension du fichier est prise en charge."""
        return path.suffix.lower() in LoaderFactory.supported_extensions()

    @staticmethod
    def for_path(path: Path) -> DocumentLoader:
        """Retourne le loader adapté au fichier, sinon UnsupportedFileTypeError."""
        suffix = path.suffix.lower()
        for loader_type in _LOADER_TYPES:
            if suffix in loader_type.supported_extensions:
                return loader_type()
        raise UnsupportedFileTypeError(
            f"Type de fichier non pris en charge : {path.name!r} "
            f"(extensions valides : {', '.join(LoaderFactory.supported_extensions())})"
        )
