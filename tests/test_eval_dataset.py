"""Tests du chargement du jeu d'évaluation (validation du schéma)."""

import json
from pathlib import Path

import pytest

from rag_core.evaluation.dataset import EvalDataset

VALID_ENTRY = {
    "id": "q01",
    "question": "Une question ?",
    "expected_source": "doc.txt",
    "expected_page": None,
    "expected_keywords": ["25 jours"],
    "should_answer": True,
}


def _write(tmp_path, payload) -> Path:
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_load_valid_dataset(tmp_path):
    cases = EvalDataset.load(_write(tmp_path, [VALID_ENTRY]))
    assert len(cases) == 1
    assert cases[0].id == "q01"
    assert cases[0].expected_keywords == ("25 jours",)
    assert cases[0].should_answer is True


def test_missing_field_raises_clear_error(tmp_path):
    broken = {key: value for key, value in VALID_ENTRY.items() if key != "expected_source"}
    path = _write(tmp_path, [broken])
    with pytest.raises(ValueError, match="expected_source"):
        EvalDataset.load(path)


def test_missing_field_reports_case_id(tmp_path):
    broken = {key: value for key, value in VALID_ENTRY.items() if key != "question"}
    path = _write(tmp_path, [broken])
    with pytest.raises(ValueError, match="q01"):
        EvalDataset.load(path)


def test_not_a_list_raises(tmp_path):
    path = _write(tmp_path, {"id": "q01"})
    with pytest.raises(ValueError, match="liste"):
        EvalDataset.load(path)


def test_multiple_cases_preserve_order(tmp_path):
    second = dict(VALID_ENTRY, id="q02")
    cases = EvalDataset.load(_write(tmp_path, [VALID_ENTRY, second]))
    assert [case.id for case in cases] == ["q01", "q02"]
