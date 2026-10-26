"""Commande de sauvegarde : `python manage.py backup_data [--output chemin]`."""

import sqlite3
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Archive data/media, data/index et la base SQLite (copie cohérente).

    L'archive ne contient jamais `.env` ni aucun secret.
    """

    help = "Sauvegarde médias, index vectoriel et base SQLite dans une archive .tar.gz."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--output", type=str, default=None,
            help="Chemin de l'archive (défaut : data/backups/ragapp_backup_<horodatage>.tar.gz).",
        )

    def handle(self, *args, **options) -> None:
        base_dir = Path(settings.BASE_DIR)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path(
            options["output"] or base_dir / "data" / "backups" / f"ragapp_backup_{timestamp}.tar.gz"
        )
        output.parent.mkdir(parents=True, exist_ok=True)

        db_path = Path(settings.DATABASES["default"]["NAME"])
        media_dir = Path(settings.MEDIA_ROOT)
        index_dir = base_dir / "data" / "index"

        # Copie cohérente de la base via l'API de sauvegarde de sqlite3
        # (évite d'archiver une base en pleine écriture).
        with tempfile.TemporaryDirectory(prefix="rag_backup_") as tmp:
            snapshot = Path(tmp) / "db.sqlite3"
            has_database = db_path.exists()
            if has_database:
                source = sqlite3.connect(db_path)
                target = sqlite3.connect(snapshot)
                try:
                    source.backup(target)
                finally:
                    source.close()
                    target.close()

            with tarfile.open(output, "w:gz") as archive:
                if has_database:
                    archive.add(snapshot, arcname="db.sqlite3")
                for directory, arcname in ((media_dir, "data/media"), (index_dir, "data/index")):
                    if directory.exists():
                        archive.add(directory, arcname=arcname)

        size_kb = output.stat().st_size // 1024
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde créée : {output} ({size_kb} Ko)"))
