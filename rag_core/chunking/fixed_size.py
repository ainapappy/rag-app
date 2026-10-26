"""Découpage à taille fixe avec fenêtre glissante et chevauchement."""

from rag_core.chunking.base import Chunker
from rag_core.models import Chunk, Document

# Fins de phrase privilégiées pour placer la coupure.
_SENTENCE_ENDINGS = (". ", "! ", "? ")


class FixedSizeChunker(Chunker):
    """Découpe par fenêtre glissante de `chunk_size` caractères, overlap `overlap`.

    La coupure recule jusqu'à une fin de phrase (ou un espace) proche de la
    limite pour ne pas couper un mot. Paramètres invalides → `ValueError`
    (choix documenté : `ConfigError` est réservé à la couche Settings).
    """

    def __init__(self, chunk_size: int = 700, overlap: int = 100) -> None:
        if chunk_size <= 0:
            raise ValueError(f"chunk_size doit être > 0 (reçu : {chunk_size})")
        if not 0 <= overlap < chunk_size:
            raise ValueError(
                f"overlap doit vérifier 0 <= overlap < chunk_size "
                f"(reçu : overlap={overlap}, chunk_size={chunk_size})"
            )
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, document: Document) -> list[Chunk]:
        text = document.content.strip()
        if not text:
            return []

        pieces: list[str] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(start + self.chunk_size, length)
            piece = text[start:end]
            if end < length:
                piece = piece[: self._find_break(piece)]
            piece = piece.strip()
            if piece:
                pieces.append(piece)
            if end >= length:
                break  # la fenêtre a atteint la fin : rien à glisser après
            # Progression garantie (jamais 0 ni négatif) : pas de boucle infinie.
            new_start = start + max(len(piece) - self.overlap, 1)
            # Aligne le départ sur un espace pour ne pas commencer en plein mot.
            space = text.find(" ", new_start)
            if space != -1 and space <= start + self.chunk_size:
                new_start = space + 1
            start = max(new_start, start + 1)

        return [self.make_chunk(document, i, piece) for i, piece in enumerate(pieces)]

    @staticmethod
    def _find_break(piece: str) -> int:
        """Position de coupure : dernière fin de phrase, sinon dernier espace."""
        sentence_cut = max(piece.rfind(ending) for ending in _SENTENCE_ENDINGS)
        # On garde la coupure dans la seconde moitié pour ne pas perdre trop de texte.
        if sentence_cut > len(piece) // 2:
            return sentence_cut + 1
        space_cut = piece.rfind(" ")
        if space_cut > 0:
            return space_cut
        return len(piece)
