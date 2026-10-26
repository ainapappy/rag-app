"""Tests de la commande backup_data : archive complète, sans .env."""

import sqlite3
import tarfile

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_backup_creates_archive_with_data_and_db(tmp_path, settings):
    """L'archive contient la base et les dossiers de données, jamais .env."""
    base = tmp_path / "app"
    (base / "data" / "media").mkdir(parents=True)
    (base / "data" / "index").mkdir(parents=True)
    (base / "data" / "media" / "doc.txt").write_text("upload", encoding="utf-8")
    (base / "data" / "index" / "index.sqlite3").write_bytes(b"sqlite")
    (base / ".env").write_text("DJANGO_SECRET_KEY=topsecret", encoding="utf-8")
    db_path = base / "db.sqlite3"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE t (x TEXT)")
    connection.commit()
    connection.close()

    settings.BASE_DIR = base
    settings.MEDIA_ROOT = base / "data" / "media"
    settings.DATABASES["default"]["NAME"] = db_path

    output = tmp_path / "out" / "sauvegarde.tar.gz"
    call_command("backup_data", output=str(output))

    assert output.exists()
    with tarfile.open(output, "r:gz") as archive:
        names = archive.getnames()
    assert "db.sqlite3" in names
    assert "data/media/doc.txt" in names
    assert "data/index/index.sqlite3" in names
    assert not any(".env" in name for name in names)


def test_backup_default_output_is_timestamped(tmp_path, settings):
    base = tmp_path / "app"
    base.mkdir()
    db_path = base / "db.sqlite3"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE t (x TEXT)")
    connection.close()

    settings.BASE_DIR = base
    settings.MEDIA_ROOT = base / "data" / "media"
    settings.DATABASES["default"]["NAME"] = db_path

    call_command("backup_data")
    backups = list((base / "data" / "backups").glob("ragapp_backup_*.tar.gz"))
    assert len(backups) == 1


def test_backup_without_database_still_archives(tmp_path, settings):
    """Pas de base existante (nouvelle installation) : l'archive est créée."""
    base = tmp_path / "app"
    base.mkdir()
    settings.BASE_DIR = base
    settings.MEDIA_ROOT = base / "data" / "media"
    settings.DATABASES["default"]["NAME"] = base / "db.sqlite3"

    output = tmp_path / "out.tar.gz"
    call_command("backup_data", output=str(output))
    assert output.exists()
    with tarfile.open(output, "r:gz") as archive:
        assert "db.sqlite3" not in archive.getnames()
