"""Tests du Retriever : filtre min_score, tri, top_k."""

import pytest

from rag_core.embeddings.fake import FakeEmbeddingProvider
from rag_core.models import Chunk
from rag_core.retrieval.retriever import Retriever
from rag_core.vectorstore.simple import SimpleVectorStore


def _store_with_texts(
    tmp_path, texts: list[str]
) -> tuple[SimpleVectorStore, FakeEmbeddingProvider]:
    store = SimpleVectorStore(tmp_path / "index")
    embeddings = FakeEmbeddingProvider(dimension=16)
    chunks = [
        Chunk(id=Chunk.make_id("doc.txt", None, i), text=text, source="doc.txt", index=i)
        for i, text in enumerate(texts)
    ]
    store.add(chunks, embeddings.embed(texts))
    return store, embeddings


def test_retrieve_returns_identical_text_first(tmp_path):
    store, embeddings = _store_with_texts(
        tmp_path, ["le chat dort sur le canapé", "la voiture roule", "le soleil brille"]
    )
    retriever = Retriever(embeddings, store, top_k=3, min_score=0.0)
    results = retriever.retrieve("le chat dort sur le canapé")
    assert results[0].chunk.text == "le chat dort sur le canapé"
    assert results[0].score == pytest.approx(1.0, abs=1e-5)


def test_retrieve_filters_below_min_score(tmp_path):
    store, embeddings = _store_with_texts(
        tmp_path, ["texte un", "texte deux", "texte trois"]
    )
    retriever = Retriever(embeddings, store, top_k=3, min_score=1.0)
    # Aucun texte identique à la requête : tout est filtré.
    assert retriever.retrieve("aucun rapport avec ces textes") == []


def test_retrieve_respects_top_k(tmp_path):
    texts = [f"texte numéro {i}" for i in range(10)]
    store, embeddings = _store_with_texts(tmp_path, texts)
    retriever = Retriever(embeddings, store, top_k=3, min_score=0.0)
    assert len(retriever.retrieve("texte numéro 5")) == 3


def test_retrieve_sorted_by_score_desc(tmp_path):
    store, embeddings = _store_with_texts(tmp_path, ["aaa", "bbb", "ccc"])
    retriever = Retriever(embeddings, store, top_k=3, min_score=0.0)
    results = retriever.retrieve("bbb")
    scores = [result.score for result in results]
    assert scores == sorted(scores, reverse=True)
    assert results[0].chunk.text == "bbb"  # texte identique → score maximal
