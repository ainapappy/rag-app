"""Validation des uploads : extension supportée et taille maximale."""

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from rag_core.loaders.factory import LoaderFactory


class UploadValidator:
    """Valide un fichier téléversé avant toute indexation.

    Version minimale (phase 06) ; le durcissement complet (type MIME réel,
    nom de fichier) viendra en phase 08. Lève `ValidationError` avec des
    messages en français, affichables tels quels dans l'admin.
    """

    def __init__(self, max_upload_mb: int | None = None) -> None:
        self._max_upload_mb = max_upload_mb

    def validate(self, uploaded_file) -> None:
        """Lève ValidationError si l'extension ou la taille est refusée."""
        name = Path(uploaded_file.name).name
        if not LoaderFactory.supports(Path(name)):
            raise ValidationError(
                f"Type de fichier non pris en charge : « {name} ». "
                f"Extensions acceptées : {', '.join(LoaderFactory.supported_extensions())}."
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
