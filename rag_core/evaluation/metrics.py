"""Métriques pures d'évaluation : Hit@k, MRR, rappel de mots-clés."""

import unicodedata


def normalize(text: str) -> str:
    """Minuscules sans accents ni diacritiques (≈ Str::ascii + lower)."""
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return without_marks.lower()


def hit_at_k(ranks: list[int | None], k: int) -> float:
    """Part des questions dont le bon document est dans les k premiers.

    `ranks` : rang (à partir de 1) du premier bon résultat par question,
    ou None si absent. Les questions sans rang comptent dans le dénominateur.
    """
    if not ranks:
        return 0.0
    hits = sum(1 for rank in ranks if rank is not None and rank <= k)
    return hits / len(ranks)


def reciprocal_rank(rank: int | None) -> float:
    """1/rang du premier bon résultat (0 si absent)."""
    if rank is None or rank <= 0:
        return 0.0
    return 1.0 / rank


def keyword_recall(keywords: tuple[str, ...], text: str) -> float:
    """Part des mots-clés présents dans le texte (casse et accents ignorés)."""
    if not keywords:
        return 0.0
    normalized_text = normalize(text)
    found = sum(1 for keyword in keywords if normalize(keyword) in normalized_text)
    return found / len(keywords)


def no_answer_correct(should_answer: bool, found: bool) -> bool:
    """Vrai si le comportement est correct : refuser quand il n'y a rien à dire."""
    return should_answer == found
