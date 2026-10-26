"""Tests des métriques d'évaluation (fonctions pures, cas limites)."""

import pytest

from rag_core.evaluation.metrics import (
    hit_at_k,
    keyword_recall,
    no_answer_correct,
    reciprocal_rank,
)


def test_hit_at_k_counts_relevant_in_top_k():
    ranks = [1, 3, None, 5]
    assert hit_at_k(ranks, k=3) == pytest.approx(2 / 4)  # rangs 1 et 3 seulement


def test_hit_at_k_empty_list_is_zero():
    assert hit_at_k([], k=5) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank(1) == pytest.approx(1.0)
    assert reciprocal_rank(4) == pytest.approx(0.25)
    assert reciprocal_rank(None) == 0.0
    assert reciprocal_rank(0) == 0.0


def test_keyword_recall_partial_match():
    recall = keyword_recall(("25 jours", "report"), "Vous avez 25 jours annuels.")
    assert recall == pytest.approx(0.5)


def test_keyword_recall_ignores_case_and_accents():
    recall = keyword_recall(("recolte", "ECHAUDAGE"), "La RÉCOLTE puis l'échaudage.")
    assert recall == pytest.approx(1.0)


def test_keyword_recall_empty_keywords_is_zero():
    assert keyword_recall((), "n'importe quel texte") == 0.0


def test_no_answer_correct_both_directions():
    assert no_answer_correct(should_answer=False, found=False) is True   # bon refus
    assert no_answer_correct(should_answer=False, found=True) is False   # aurait dû refuser
    assert no_answer_correct(should_answer=True, found=True) is True
    assert no_answer_correct(should_answer=True, found=False) is False
