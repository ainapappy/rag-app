"""Découpage par paragraphes : fusion des petits, découpe des trop longs."""

import re

from rag_core.chunking.base import Chunker
from rag_core.chunking.fixed_size import FixedSizeChunker
from rag_core.models import Chunk, Document

# Séparateur de paragraphes : lignes vides (avec éventuellement des espaces).
_PARAGRAPH_PATTERN = re.compile(r"\n\s*\n")


class ParagraphChunker(Chunker):
    """Découpe sur les lignes vides, fusionne les petits paragraphes.

    Les paragraphes plus longs que `max_size` sont délégués à un
    `FixedSizeChunker` pour garantir qu'aucun chunk ne dépasse la limite.
    """

    def __init__(self, max_size: int = 700) -> None:
        if max_size <= 0:
            raise ValueError(f"max_size doit être > 0 (reçu : {max_size})")
        self.max_size = max_size
        # Chevauchement interne raisonnable pour les paragraphes trop longs.
        internal_overlap = min(100, max_size - 1)
        self._fixed = FixedSizeChunker(chunk_size=max_size, overlap=internal_overlap)

    def split(self, document: Document) -> list[Chunk]:
        paragraphs = [
            paragraph.strip()
            for paragraph in _PARAGRAPH_PATTERN.split(document.content)
            if paragraph.strip()
        ]

        pieces: list[str] = []
        buffer = ""
        for paragraph in paragraphs:
            if len(paragraph) > self.max_size:
                # Trop long : on vide le tampon puis on délègue au chunker fixe.
                if buffer:
                    pieces.append(buffer)
                    buffer = ""
                sub_document = Document(
                    source=document.source,
                    content=paragraph,
                    page=document.page,
                    metadata=document.metadata,
                )
                pieces.extend(chunk.text for chunk in self._fixed.split(sub_document))
            elif buffer and len(buffer) + 2 + len(paragraph) > self.max_size:
                pieces.append(buffer)
                buffer = paragraph
            else:
                buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
        if buffer:
            pieces.append(buffer)

        return [self.make_chunk(document, i, piece) for i, piece in enumerate(pieces)]
