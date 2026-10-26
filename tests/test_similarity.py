"""Tests de la similarité cosinus."""

import numpy as np
import pytest

from rag_core.embeddings.similarity import cosine_similarity, cosine_similarity_matrix


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ([1, 0], [1, 0], 1.0),      # identiques
        ([1, 0], [2, 0], 1.0),      # colinéaires (même direction)
        ([1, 0], [0, 1], 0.0),      # orthogonaux
        ([1, 0], [-1, 0], -1.0),    # opposés
    ],
)
def test_cosine_similarity_known_cases(a, b, expected):
    assert cosine_similarity(a, b) == pytest.approx(expected, abs=1e-6)


def test_cosine_similarity_zero_vector_is_safe():
    """Vecteur nul : renvoie 0.0 sans lever de division par zéro."""
    assert cosine_similarity([0, 0, 0], [1, 2, 3]) == 0.0
    assert cosine_similarity([1, 2, 3], [0, 0, 0]) == 0.0


def test_cosine_similarity_matrix_matches_scalar():
    query = [1.0, 2.0]
    matrix = np.array([[1.0, 2.0], [0.0, 1.0], [0.0, 0.0]])
    scores = cosine_similarity_matrix(query, matrix)
    assert scores[0] == pytest.approx(1.0, abs=1e-6)
    assert scores[1] == pytest.approx(cosine_similarity(query, [0, 1]), abs=1e-6)
    assert scores[2] == 0.0  # ligne nulle


def test_cosine_similarity_matrix_empty():
    scores = cosine_similarity_matrix([1.0], np.zeros((0, 1), dtype=np.float32))
    assert len(scores) == 0
