"""Chargement et validation du jeu de questions d'évaluation (JSON)."""

import json
from pathlib import Path

from rag_core.evaluation.models import EvalCase

REQUIRED_FIELDS = {
    "id",
    "question",
    "expected_source",
    "expected_page",
    "expected_keywords",
    "should_answer",
}


class EvalDataset:
    """Charge un fichier JSON de questions avec validation du schéma."""

    @staticmethod
    def load(path: Path) -> list[EvalCase]:
        """Lit le fichier ; erreur claire si le schéma est incomplet."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(
                f"{path} : le fichier doit contenir une liste d'objets JSON."
            )
        cases: list[EvalCase] = []
        for index, entry in enumerate(data):
            if not isinstance(entry, dict):
                raise ValueError(f"{path} : entrée {index} n'est pas un objet JSON.")
            missing = REQUIRED_FIELDS - set(entry)
            if missing:
                raise ValueError(
                    f"{path} : entrée {index} ({entry.get('id', '?')}) — "
                    f"champs manquants : {', '.join(sorted(missing))}"
                )
            cases.append(
                EvalCase(
                    id=entry["id"],
                    question=entry["question"],
                    expected_source=entry["expected_source"],
                    expected_page=entry["expected_page"],
                    expected_keywords=tuple(entry["expected_keywords"]),
                    should_answer=bool(entry["should_answer"]),
                )
            )
        return cases
