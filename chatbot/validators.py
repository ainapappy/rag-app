"""Validation des uploads : extension, taille, octets magiques, nom nettoyé.

Même validateur pour l'admin et l'API : aucune duplication.
Erreurs → `django.core.exceptions.ValidationError`
(affichée par l'admin, convertie en 422 par l'API).
"""

import logging
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from rag_core.loaders.factory import LoaderFactory

logger = logging.getLogger(__name__)

MAX_NAME_LENGTH = 255
# Octets magiques d'un PDF valide (spécification ISO 32000).
PDF_MAGIC = b"%PDF-"


class UploadValidator:
    """Valide un fichier téléversé avant toute indexation.

    Vérifie, dans l'ordre : nom de fichier nettoyable, extension supportée,
    taille maximale, contenu réel (octets magiques pour les PDF).
    """

    def __init__(self, max_mb: int | None = None, loader_factory=LoaderFactory) -> None:
        self._max_upload_mb = max_mb
        self._loader_factory = loader_factory

    def validate(self, uploaded_file) -> None:
        """Lève ValidationError si le fichier est refusé."""
        clean_name = self.clean_name(uploaded_file.name)
        if not self._loader_factory.supports(Path(clean_name)):
            raise ValidationError(
                f"Type de fichier non pris en charge : « {clean_name} ». "
                f"Extensions acceptées : {', '.join(self._loader_factory.supported_extensions())}."
            )
        max_mb = (
            self._max_upload_mb
            if self._max_upload_mb is not None
            else getattr(settings, "MAX_UPLOAD_MB", 10)
        )
        limit_bytes = max_mb * 1024 * 1024
        if uploaded_file.size > limit_bytes:
            raise ValidationError(
                f"Fichier trop volumineux ({uploaded_file.size // (1024 * 1024) + 1} Mo) : "
                f"la limite est de {max_mb} Mo (MAX_UPLOAD_MB)."
            )
        if Path(clean_name).suffix.lower() == ".pdf":
            self._check_pdf_magic(uploaded_file)

    @staticmethod
    def clean_name(name: str) -> str:
        """Supprime tout chemin (Windows/Unix), limite la longueur."""
        clean = Path(name.replace("\\", "/")).name
        if not clean or clean in {".", ".."}:
            raise ValidationError("Nom de fichier invalide.")
        if len(clean) > MAX_NAME_LENGTH:
            raise ValidationError(
                f"Nom de fichier trop long (maximum {MAX_NAME_LENGTH} caractères)."
            )
        return clean

    @staticmethod
    def _check_pdf_magic(uploaded_file) -> None:
        """Un « .pdf » doit vraiment commencer par %PDF- (pas une extension seule)."""
        header = uploaded_file.read(len(PDF_MAGIC))
        uploaded_file.seek(0)  # indispensable : le fichier sera relu à l'enregistrement
        if header != PDF_MAGIC:
            logger.warning("Upload refusé : pseudo-PDF sans signature %PDF-.")
            raise ValidationError(
                "Fichier PDF invalide : le contenu ne correspond pas à un PDF "
                "(signature %PDF- absente)."
            )
