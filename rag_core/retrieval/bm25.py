"""BM25 écrit à la main : recherche lexicale (mots exacts) complémentaire.

≈ 60 lignes, aucune dépendance : tokenisation minuscule sans accents,
paramètres classiques k1=1.5, b=0.75. Complète la recherche sémantique
pour les requêtes avec mots rares exacts (noms propres, codes).
"""

import math
import re
import unicodedata

from rag_core.models import Chunk

_TOKEN_PATTERN = re.compile(r"\w+")
K1 = 1.5
B = 0.75


def tokenize(text: str) -> list[str]:
    """Minuscules, accents retirés, découpage sur les caractères non-alfanumériques."""
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return _TOKEN_PATTERN.findall(without_marks.lower())


class Bm25Index:
    """Index BM25 en mémoire, construit à partir des chunks du store."""

    def __init__(self, chunks: list[Chunk], k1: float = K1, b: float = B) -> None:
        self._k1 = k1
        self._b = b
        self._chunks = chunks
        self._term_counts: list[dict[str, int]] = []
        self._doc_lengths: list[int] = []
        document_frequency: dict[str, int] = {}

        for chunk in chunks:
            tokens = tokenize(chunk.text)
            counts: dict[str, int] = {}
            for token in tokens:
                counts[token] = counts.get(token, 0) + 1
            self._term_counts.append(counts)
            self._doc_lengths.append(len(tokens))
            for term in counts:
                document_frequency[term] = document_frequency.get(term, 0) + 1

        total = len(chunks)
        self._avgdl = (sum(self._doc_lengths) / total) if total else 0.0
        # IDF lissé (style Okapi : log((N - df + 0.5) / (df + 0.5) + 1)).
        self._idf = {
            term: math.log((total - df + 0.5) / (df + 0.5) + 1.0)
            for term, df in document_frequency.items()
        }

    @classmethod
    def from_store(cls, store) -> "Bm25Index":
        """Construit l'index depuis tous les chunks du store."""
        return cls(list(store.iter_chunks()))

    def search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        """Renvoie les (chunk, score) BM25 triés par score décroissant."""
        if not self._chunks or top_k <= 0:
            return []
        query_tokens = tokenize(query)
        scores: list[float] = []
        for counts, length in zip(self._term_counts, self._doc_lengths, strict=True):
            score = 0.0
            for term in query_tokens:
                frequency = counts.get(term, 0)
                if frequency == 0:
                    continue
                idf = self._idf.get(term, 0.0)
                denominator = frequency + self._k1 * (
                    1 - self._b + self._b * (length / self._avgdl if self._avgdl else 0)
                )
                score += idf * frequency * (self._k1 + 1) / denominator
            scores.append(score)

        order = sorted(range(len(self._chunks)), key=lambda i: scores[i], reverse=True)
        return [(self._chunks[i], scores[i]) for i in order[:top_k] if scores[i] > 0]
