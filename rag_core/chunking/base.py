"""Interface abstraite des découpeurs de documents (chunkers)."""

from abc import ABC, abstractmethod

from rag_core.models import Chunk, Document


class Chunker(ABC):
    """Contrat commun aux stratégies de découpage en chunks."""

    @abstractmethod
    def split(self, document: Document) -> list[Chunk]:
        """Découpe un document en chunks (index à partir de 0 par document)."""

    def make_chunk(self, document: Document, index: int, text: str) -> Chunk:
        """Construit un Chunk cohérent : id déterministe + métadonnées du document.

        Règle du projet : un chunk garde toujours `source`, `page` et `index`.
        """
        return Chunk(
            id=Chunk.make_id(document.source, document.page, index),
            text=text,
            source=document.source,
            page=document.page,
            index=index,
            metadata={**document.metadata, "chunk_chars": len(text)},
        )
