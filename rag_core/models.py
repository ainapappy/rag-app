"""Objets-valeurs du cœur RAG (dataclasses immuables, ≈ DTO Laravel)."""

import hashlib
from dataclasses import dataclass, field

# Rôles valides d'un message de conversation (convention API OpenAI).
VALID_ROLES = {"system", "user", "assistant"}


@dataclass(frozen=True)
class ChatMessage:
    """Un message de conversation : rôle + contenu, immuable.

    Levée de `ValueError` si le rôle est invalide (validation dans
    `__post_init__`, l'équivalent du constructeur/boots d'un DTO).
    """

    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in VALID_ROLES:
            raise ValueError(
                f"Rôle invalide : {self.role!r} (attendu parmi {sorted(VALID_ROLES)})"
            )

    def to_dict(self) -> dict[str, str]:
        """Convertit le message au format attendu par l'API OpenAI."""
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class Document:
    """Un document chargé en mémoire (une entrée par page pour les PDF).

    `source` est le nom du fichier (ex. « guide.pdf ») ; `page` commence
    à 1 pour les PDF et vaut None pour les fichiers sans pagination.
    """

    source: str
    content: str
    page: int | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    """Un fragment de document indexé, avec sa source et sa position.

    `id` est calculé par `Chunk.make_id` (sha1 déterministe) pour que le
    même (source, page, index) donne toujours la même clé d'upsert.
    """

    id: str
    text: str
    source: str
    page: int | None = None
    index: int = 0
    metadata: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def make_id(source: str, page: int | None, index: int) -> str:
        """Identifiant déterministe : mêmes (source, page, index) → même id."""
        key = f"{source}::{page if page is not None else -1}::{index}"
        return hashlib.sha1(key.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SearchResult:
    """Résultat d'une recherche vectorielle : le chunk et son score."""

    chunk: Chunk
    score: float
