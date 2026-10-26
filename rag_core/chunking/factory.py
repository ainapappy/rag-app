"""Factory des chunkers : stratégie `fixed` ou `paragraph` selon les Settings."""

from rag_core.chunking.base import Chunker
from rag_core.chunking.fixed_size import FixedSizeChunker
from rag_core.chunking.paragraph import ParagraphChunker
from rag_core.exceptions import ConfigError
from rag_core.settings import Settings


class ChunkerFactory:
    """Construit le chunker configuré (taille et overlap venant des Settings)."""

    @staticmethod
    def create(settings: Settings) -> Chunker:
        """Retourne le Chunker correspondant à `CHUNKER_STRATEGY`."""
        if settings.chunker_strategy == "fixed":
            return FixedSizeChunker(
                chunk_size=settings.chunk_size, overlap=settings.chunk_overlap
            )
        if settings.chunker_strategy == "paragraph":
            return ParagraphChunker(max_size=settings.chunk_size)
        raise ConfigError(
            f"Stratégie de chunking inconnue : {settings.chunker_strategy!r} "
            "(attendu : fixed, paragraph)"
        )
