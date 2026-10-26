"""Similarité cosinus, vectorisée avec NumPy."""

import numpy as np


def cosine_similarity(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    """Similarité cosinus entre deux vecteurs (1 = identiques, 0 = sans rapport).

    Renvoie 0.0 si l'un des vecteurs est nul (pas de division par zéro).
    """
    a_arr = np.asarray(a, dtype=np.float32)
    b_arr = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(a_arr) * np.linalg.norm(b_arr))
    if denom == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


def cosine_similarity_matrix(query: list[float] | np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Similarité cosinus entre un vecteur requête et chaque ligne d'une matrice.

    Renvoie un tableau de taille `len(matrix)` ; 0.0 pour les lignes nulles.
    """
    q = np.asarray(query, dtype=np.float32)
    m = np.asarray(matrix, dtype=np.float32)
    if m.size == 0:
        return np.zeros(m.shape[0], dtype=np.float32)
    norms = np.linalg.norm(m, axis=1) * np.linalg.norm(q)
    scores = np.zeros(m.shape[0], dtype=np.float32)
    mask = norms > 0
    scores[mask] = (m[mask] @ q) / norms[mask]
    return scores
