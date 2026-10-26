"""Tests des chunkers (fixed et paragraph) : tailles, overlap, indices, ids."""

import pytest

from rag_core.chunking.factory import ChunkerFactory
from rag_core.chunking.fixed_size import FixedSizeChunker
from rag_core.chunking.paragraph import ParagraphChunker
from rag_core.models import Chunk, Document
from rag_core.settings import Settings


def _doc(content: str, source: str = "test.txt", page: int | None = None) -> Document:
    return Document(source=source, content=content, page=page)


# ---------------------------------------------------------------------------
# FixedSizeChunker
# ---------------------------------------------------------------------------


def test_fixed_respects_max_size():
    chunker = FixedSizeChunker(chunk_size=100, overlap=20)
    chunks = chunker.split(_doc(" ".join(f"mot{i}" for i in range(500))))
    assert len(chunks) > 1
    assert all(len(chunk.text) <= 100 for chunk in chunks)


def test_fixed_has_overlap_between_consecutive_chunks():
    """Sans espace à reculer, l'overlap est exact : N caractères communs."""
    chunker = FixedSizeChunker(chunk_size=100, overlap=20)
    text = "x" * 500  # aucun espace : coupure exactement à chunk_size
    chunks = chunker.split(_doc(text))
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert current.text[:20] == previous.text[-20:]


def test_fixed_cuts_at_sentence_or_space():
    """Avec un texte naturel, aucun chunk ne se termine au milieu d'un mot."""
    chunker = FixedSizeChunker(chunk_size=80, overlap=10)
    text = ". ".join(f"Phrase numéro {i} raconte une histoire" for i in range(40)) + "."
    chunks = chunker.split(_doc(text))
    assert all(chunk.text and chunk.text[-1] != " " for chunk in chunks)
    # aucun mot coupé : chaque chunk est fait de mots entiers du texte d'origine
    words = set(text.split())
    for chunk in chunks:
        assert set(chunk.text.split()) <= words


def test_fixed_no_empty_chunks_and_consecutive_indices():
    chunker = FixedSizeChunker(chunk_size=50, overlap=10)
    text = "abc def ghi " * 40
    chunks = chunker.split(_doc(text))
    assert all(chunk.text.strip() for chunk in chunks)
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))


def test_fixed_short_text_single_chunk():
    chunker = FixedSizeChunker(chunk_size=700, overlap=100)
    chunks = chunker.split(_doc("Court texte."))
    assert len(chunks) == 1
    assert chunks[0].text == "Court texte."


def test_fixed_deterministic_unique_ids():
    chunker = FixedSizeChunker(chunk_size=100, overlap=20)
    document = _doc("contenu " * 200)
    first = chunker.split(document)
    second = chunker.split(document)
    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert len({chunk.id for chunk in first}) == len(first)
    assert first[0].id == Chunk.make_id(document.source, document.page, 0)


def test_fixed_chunks_carry_document_metadata_and_size():
    document = Document(
        source="rapport.pdf", content="x" * 300, page=2, metadata={"title": "Rapport"}
    )
    chunks = FixedSizeChunker(chunk_size=100, overlap=20).split(document)
    assert chunks[0].page == 2
    assert chunks[0].metadata["title"] == "Rapport"
    assert chunks[0].metadata["chunk_chars"] == len(chunks[0].text)
    assert chunks[0].id == Chunk.make_id("rapport.pdf", 2, 0)


def test_fixed_empty_content_returns_no_chunk():
    assert FixedSizeChunker().split(_doc("   \n  ")) == []


@pytest.mark.parametrize(
    ("size", "overlap"), [(0, 0), (-10, 0), (100, 100), (100, 150), (100, -1)]
)
def test_fixed_invalid_parameters_raise(size, overlap):
    with pytest.raises(ValueError):
        FixedSizeChunker(chunk_size=size, overlap=overlap)


def test_fixed_never_loops_forever():
    """Cas extrêmes : la boucle doit toujours progresser et se terminer."""
    chunker = FixedSizeChunker(chunk_size=10, overlap=9)
    chunks = chunker.split(_doc("ab cd ef gh ij kl mn op qr st uv wx yz"))
    assert len(chunks) > 1  # terminé sans blocage


# ---------------------------------------------------------------------------
# ParagraphChunker
# ---------------------------------------------------------------------------


def test_paragraph_merges_small_paragraphs():
    paragraphs = "\n\n".join(f"Paragraphe court numéro {i} avec du texte." for i in range(5))
    chunks = ParagraphChunker(max_size=200).split(_doc(paragraphs))
    assert len(chunks) < 5  # fusionné en 1 ou 2 chunks
    assert all(len(chunk.text) <= 200 for chunk in chunks)


def test_paragraph_splits_long_paragraph():
    long_paragraph = " ".join(f"mot{i}" for i in range(400))
    chunks = ParagraphChunker(max_size=100).split(_doc(long_paragraph))
    assert len(chunks) > 1
    assert all(len(chunk.text) <= 100 for chunk in chunks)


def test_paragraph_mixed_case():
    small = "\n\n".join("Petit paragraphe." for _ in range(3))
    big = "Long " * 300
    chunks = ParagraphChunker(max_size=150).split(_doc(f"{small}\n\n{big}"))
    assert all(len(chunk.text) <= 150 for chunk in chunks)
    assert any("Petit paragraphe" in chunk.text for chunk in chunks)


def test_paragraph_consecutive_indices_and_ids():
    content = "\n\n".join(f"Paragraphe {i}. " + "x " * 60 for i in range(6))
    chunks = ParagraphChunker(max_size=100).split(_doc(content, source="doc.md", page=3))
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.id == Chunk.make_id("doc.md", 3, chunk.index) for chunk in chunks)


def test_paragraph_invalid_max_size_raises():
    with pytest.raises(ValueError):
        ParagraphChunker(max_size=0)


# ---------------------------------------------------------------------------
# ChunkerFactory
# ---------------------------------------------------------------------------


def test_factory_creates_fixed_chunker(monkeypatch):
    monkeypatch.setenv("CHUNKER_STRATEGY", "fixed")
    monkeypatch.setenv("CHUNK_SIZE", "300")
    monkeypatch.setenv("CHUNK_OVERLAP", "50")
    chunker = ChunkerFactory.create(Settings(_env_file=None))
    assert isinstance(chunker, FixedSizeChunker)
    assert chunker.chunk_size == 300
    assert chunker.overlap == 50


def test_factory_creates_paragraph_chunker(monkeypatch):
    monkeypatch.setenv("CHUNKER_STRATEGY", "paragraph")
    monkeypatch.setenv("CHUNK_SIZE", "250")
    monkeypatch.setenv("CHUNK_OVERLAP", "40")  # ignoré pour paragraph
    chunker = ChunkerFactory.create(Settings(_env_file=None))
    assert isinstance(chunker, ParagraphChunker)
    assert chunker.max_size == 250
