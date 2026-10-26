"""Tests des chargeurs de documents (txt, md, pdf) et de la LoaderFactory."""

import pytest

from rag_core.exceptions import LoaderError, UnsupportedFileTypeError
from rag_core.loaders.factory import LoaderFactory
from rag_core.loaders.markdown import MarkdownLoader
from rag_core.loaders.pdf import PdfLoader
from rag_core.loaders.txt import TxtLoader

# ---------------------------------------------------------------------------
# TxtLoader
# ---------------------------------------------------------------------------


def test_txt_loader_utf8(tmp_path):
    file = tmp_path / "note.txt"
    file.write_text("Première ligne avec accents : éàü.\nDeuxième ligne.", encoding="utf-8")
    documents = TxtLoader().load(file)
    assert len(documents) == 1
    assert documents[0].source == "note.txt"
    assert documents[0].page is None
    assert "éàü" in documents[0].content


def test_txt_loader_falls_back_to_latin1(tmp_path):
    """Octet 0xE9 invalide en UTF-8 : repli latin-1 sans lever d'erreur."""
    file = tmp_path / "ancien.txt"
    file.write_bytes(b"caf\xe9 noir")  # "café noir" en latin-1
    documents = TxtLoader().load(file)
    assert documents[0].content == "café noir"


def test_txt_loader_custom_source(tmp_path):
    file = tmp_path / "note.txt"
    file.write_text("contenu", encoding="utf-8")
    documents = TxtLoader().load(file, source="origine/note.txt")
    assert documents[0].source == "origine/note.txt"


# ---------------------------------------------------------------------------
# MarkdownLoader
# ---------------------------------------------------------------------------


def test_markdown_loader_extracts_title(tmp_path):
    file = tmp_path / "guide.md"
    file.write_text("# Mon titre\n\nDu contenu **important**.\n", encoding="utf-8")
    documents = MarkdownLoader().load(file)
    assert documents[0].metadata["title"] == "Mon titre"
    assert "# Mon titre" in documents[0].content  # texte brut conservé


def test_markdown_loader_without_title(tmp_path):
    file = tmp_path / "sans_titre.md"
    file.write_text("Juste du texte.\n", encoding="utf-8")
    documents = MarkdownLoader().load(file)
    assert "title" not in documents[0].metadata


# ---------------------------------------------------------------------------
# PdfLoader (PDF générés avec reportlab)
# ---------------------------------------------------------------------------


def _make_pdf(path, pages_texts: list[str]) -> None:
    from reportlab.pdfgen import canvas

    canvas_obj = canvas.Canvas(str(path))
    for text in pages_texts:
        canvas_obj.drawString(72, 750, text)
        canvas_obj.showPage()
    canvas_obj.save()


def test_pdf_loader_one_document_per_page(tmp_path):
    file = tmp_path / "rapport.pdf"
    _make_pdf(file, ["Page un : chiffre 42", "Page deux : chiffre 99", "Page trois."])
    documents = PdfLoader().load(file)
    assert [doc.page for doc in documents] == [1, 2, 3]
    assert "42" in documents[0].content
    assert "99" in documents[1].content


def test_pdf_loader_skips_empty_pages(tmp_path):
    file = tmp_path / "trous.pdf"
    _make_pdf(file, ["Premiere page", "", "Troisieme page"])
    documents = PdfLoader().load(file)
    assert [doc.page for doc in documents] == [1, 3]


def test_pdf_loader_scanned_pdf_raises(tmp_path):
    """PDF sans texte extractible → LoaderError avec message OCR."""
    file = tmp_path / "scanne.pdf"
    _make_pdf(file, ["", ""])  # pages sans texte
    with pytest.raises(LoaderError, match="OCR"):
        PdfLoader().load(file)


def test_pdf_loader_corrupted_file_raises(tmp_path):
    file = tmp_path / "casse.pdf"
    file.write_bytes(b"ceci n'est pas un pdf")
    with pytest.raises(LoaderError):
        PdfLoader().load(file)


# ---------------------------------------------------------------------------
# LoaderFactory
# ---------------------------------------------------------------------------


def test_factory_lists_supported_extensions():
    extensions = LoaderFactory.supported_extensions()
    assert ".txt" in extensions
    assert ".md" in extensions
    assert ".pdf" in extensions


@pytest.mark.parametrize(
    "filename", ["doc.txt", "DOC.TXT", "note.md", "rapport.pdf", "sansextension"]
)
def test_factory_supports(filename, tmp_path):
    assert LoaderFactory.supports(tmp_path / filename) == filename.lower().endswith(
        (".txt", ".md", ".pdf")
    )


def test_factory_for_path_returns_right_loader(tmp_path):
    assert isinstance(LoaderFactory.for_path(tmp_path / "a.txt"), TxtLoader)
    assert isinstance(LoaderFactory.for_path(tmp_path / "b.md"), MarkdownLoader)
    assert isinstance(LoaderFactory.for_path(tmp_path / "c.pdf"), PdfLoader)


def test_factory_for_path_unknown_extension_raises(tmp_path):
    with pytest.raises(UnsupportedFileTypeError):
        LoaderFactory.for_path(tmp_path / "image.png")
