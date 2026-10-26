"""Évaluateur RAG : mesure la récupération (et la réponse si LLM fourni)."""

from rag_core.evaluation.metrics import (
    hit_at_k,
    keyword_recall,
    no_answer_correct,
    reciprocal_rank,
)
from rag_core.evaluation.models import CaseResult, EvalCase, EvalReport
from rag_core.retrieval.retriever import Retriever


class RagEvaluator:
    """Évalue un retriever (et optionnellement un pipeline LLM) sur un jeu de cas.

    Fonctionne sans LLM : seules la récupération et les refus sont mesurés.
    Avec un `pipeline`, mesure en plus le rappel des mots-clés attendus dans
    la réponse générée ; avec un `judge`, la fidélité au contexte.
    """

    def __init__(self, retriever: Retriever, pipeline=None, judge=None) -> None:
        self._retriever = retriever
        self._pipeline = pipeline
        self._judge = judge

    def evaluate(self, cases: list[EvalCase]) -> EvalReport:
        """Évalue chaque cas puis agrège les métriques."""
        case_results = [self._evaluate_case(case) for case in cases]

        k = getattr(self._retriever, "top_k", 4)
        ranks = [result.rank for result in case_results if result.case.should_answer]
        refusable = [result for result in case_results if not result.case.should_answer]
        recalls = [
            result.keyword_recall
            for result in case_results
            if result.keyword_recall is not None
        ]
        faithful = [
            result.faithfulness
            for result in case_results
            if result.faithfulness is not None
        ]

        return EvalReport(
            hit_at_k=hit_at_k(ranks, k),
            mrr=_mean([reciprocal_rank(rank) for rank in ranks]),
            no_answer_rate=(
                _mean([1.0 if result.no_answer_correct else 0.0 for result in refusable])
                if refusable
                else None
            ),
            keyword_recall=_mean(recalls) if recalls else None,
            faithfulness=_mean([1.0 if value else 0.0 for value in faithful])
            if faithful
            else None,
            cases=tuple(case_results),
        )

    def _evaluate_case(self, case: EvalCase) -> CaseResult:
        """Évalue un cas : rang du bon document, refus, réponse si LLM."""
        results = self._retriever.retrieve(case.question)
        found = bool(results)

        rank: int | None = None
        page_ok: bool | None = None
        for position, result in enumerate(results, start=1):
            if case.expected_source is None or result.chunk.source != case.expected_source:
                continue
            if rank is None:
                rank = position
                if case.expected_page is not None:
                    page_ok = result.chunk.page == case.expected_page

        recall: float | None = None
        faithfulness: bool | None = None
        answer_text: str | None = None
        if self._pipeline is not None:
            answer = self._pipeline.ask(case.question)
            found = answer.found
            answer_text = answer.text
            if case.should_answer:
                recall = keyword_recall(case.expected_keywords, answer.text)
                if self._judge is not None and answer.found:
                    context = "\n\n".join(result.chunk.text for result in results)
                    faithfulness = self._judge.is_faithful(
                        case.question, context, answer.text
                    )

        return CaseResult(
            case=case,
            found=found,
            hit=rank is not None,
            rank=rank,
            page_ok=page_ok,
            no_answer_correct=no_answer_correct(case.should_answer, found),
            keyword_recall=recall,
            faithfulness=faithfulness,
            answer=answer_text,
        )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
