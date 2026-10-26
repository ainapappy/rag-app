"""Objets-valeurs de l'évaluation (≈ DTO de rapport de tests)."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvalCase:
    """Une question de référence et sa réponse attendue."""

    id: str
    question: str
    expected_source: str | None
    expected_page: int | None
    expected_keywords: tuple[str, ...]
    should_answer: bool


@dataclass(frozen=True)
class CaseResult:
    """Résultat d'évaluation d'un cas : récupération + réponse éventuelle."""

    case: EvalCase
    found: bool                 # le système a-t-il produit une réponse ?
    hit: bool                   # la source attendue est-elle dans le top-k ?
    rank: int | None            # rang (à partir de 1) du premier bon résultat
    page_ok: bool | None        # page correcte si une page était attendue
    no_answer_correct: bool     # refuse quand il faut, répond quand il faut
    keyword_recall: float | None = None  # si LLM : mots-clés présents dans la réponse
    faithfulness: bool | None = None     # si juge : réponse soutenue par le contexte ?
    answer: str | None = None            # texte généré (mode --with-llm)


@dataclass(frozen=True)
class EvalReport:
    """Métriques agrégées + détail par question."""

    hit_at_k: float
    mrr: float
    no_answer_rate: float | None       # None si aucun cas « sans réponse »
    keyword_recall: float | None       # None si éval sans LLM
    faithfulness: float | None         # None sans juge
    cases: tuple[CaseResult, ...] = field(default_factory=tuple)
