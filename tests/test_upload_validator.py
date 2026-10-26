"""Tests du validateur d'upload : extension, taille, magic bytes, nom."""

import pytest
from django.core.exceptions import ValidationError

from chatbot.validators import UploadValidator


class DummyUpload:
    """Double minimal d'un fichier téléversé (name, size, read, seek)."""

    def __init__(self, name: str, content: bytes = b"ok", size: int | None = None) -> None:
        self.name = name
        self._content = content
        self.size = size if size is not None else len(content)

    def read(self, n: int = -1) -> bytes:
        return self._content[:n] if n >= 0 else self._content

    def seek(self, pos: int) -> None:
        pass


def test_valid_txt_accepted():
    UploadValidator().validate(DummyUpload("note.txt"))  # ne lève pas


def test_valid_pdf_magic_bytes_accepted():
    UploadValidator().validate(DummyUpload("doc.pdf", b"%PDF-1.7 contenu"))  # ne lève pas


def test_fake_pdf_refused_by_magic_bytes():
    with pytest.raises(ValidationError, match="signature"):
        UploadValidator().validate(DummyUpload("doc.pdf", b"PK\x03\x04 pas un pdf"))


def test_pdf_file_pointer_reset_after_check():
    """Le curseur est remis à 0 : le fichier est intégral à la sauvegarde."""
    upload = DummyUpload("doc.pdf", b"%PDF-1.7")
    UploadValidator().validate(upload)
    assert upload.read().startswith(b"%PDF-")


def test_unsupported_extension_refused():
    with pytest.raises(ValidationError, match="non pris en charge"):
        UploadValidator().validate(DummyUpload("prog.exe", b"MZ"))


def test_too_big_refused():
    upload = DummyUpload("gros.txt", size=2 * 1024 * 1024)
    with pytest.raises(ValidationError, match="trop volumineux"):
        UploadValidator(max_mb=1).validate(upload)


def test_max_mb_zero_refuses_everything():
    with pytest.raises(ValidationError, match="trop volumineux"):
        UploadValidator(max_mb=0).validate(DummyUpload("note.txt"))


def test_path_traversal_name_is_cleaned():
    """« ../../evil.pdf » est réduit à « evil.pdf » puis validé normalement."""
    UploadValidator().validate(DummyUpload("../../evil.pdf", b"%PDF-1.7"))  # ne lève pas


def test_backslash_path_cleaned():
    UploadValidator().validate(DummyUpload("C:\\dossier\\secret.txt"))  # ne lève pas


def test_too_long_filename_refused():
    with pytest.raises(ValidationError, match="trop long"):
        UploadValidator().validate(DummyUpload("a" * 300 + ".txt"))


def test_empty_name_refused():
    with pytest.raises(ValidationError, match="invalide"):
        UploadValidator().validate(DummyUpload(""))
