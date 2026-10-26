"""Suite de contrat : mêmes tests sur SimpleVectorStore et ChromaVectorStore."""

import threading
from pathlib import Path

import pytest

from rag_core.embeddings.fake import FakeEmbeddingProvider
from rag_core.models import Chunk
from rag_core.vectorstore.base import VectorStore
from rag_core.vectorstore.chroma import ChromaVectorStore
from rag_core.vectorstore.simple import SimpleVectorStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(impl: str, path: Path) -> VectorStore:
    if impl == "simple":
        return SimpleVectorStore(path)
    pytest.importorskip("chromadb")
    return ChromaVectorStore(path)


def _chunks_for(source: str, texts: list[str], file_hash: str | None = None) -> list[Chunk]:
    metadata = {"file_hash": file_hash} if file_hash is not None else {}
    return [
        Chunk(
            id=Chunk.make_id(source, None, i),
            text=text,
            source=source,
            page=None,
            index=i,
            metadata=dict(metadata),
        )
        for i, text in enumerate(texts)
    ]


@pytest.fixture(params=["simple", "chroma"])
def store(request, tmp_path):
    """La même suite de contrat tourne sur les deux implémentations."""
    return _make_store(request.param, tmp_path / "index")


# ---------------------------------------------------------------------------
# Contrat commun
# ---------------------------------------------------------------------------


def test_add_and_count(store):
    texts = ["le chat dort", "la voiture roule", "le soleil brille"]
    vectors = FakeEmbeddingProvider(dimension=16).embed(texts)
    store.add(_chunks_for("doc1.txt", texts, file_hash="hash-1"), vectors)
    assert store.count() == 3


def test_search_returns_sorted_top_k(store):
    provider = FakeEmbeddingProvider(dimension=16)
    texts = ["le chat dort", "la voiture roule", "le soleil brille"]
    store.add(_chunks_for("doc1.txt", texts, "h1"), provider.embed(texts))
    results = store.search(provider.embed_query("le chat dort"), top_k=2)
    assert len(results) == 2
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)  # tri décroissant
    assert results[0].chunk.text == "le chat dort"  # texte identique → score max
    assert results[0].score == pytest.approx(1.0, abs=1e-5)


def test_search_top_k_larger_than_index(store):
    provider = FakeEmbeddingProvider(dimension=16)
    store.add(_chunks_for("doc1.txt", ["seul texte"], "h1"), provider.embed(["seul texte"]))
    assert len(store.search(provider.embed_query("n'importe quoi"), top_k=10)) == 1


def test_delete_by_source(store):
    provider = FakeEmbeddingProvider(dimension=16)
    store.add(_chunks_for("doc1.txt", ["a", "b"], "h1"), provider.embed(["a", "b"]))
    store.add(_chunks_for("doc2.txt", ["c"], "h2"), provider.embed(["c"]))
    deleted = store.delete_by_source("doc1.txt")
    assert deleted == 2
    assert store.count() == 1
    assert store.list_sources() == ["doc2.txt"]


def test_delete_unknown_source_returns_zero(store):
    assert store.delete_by_source("inexistant.txt") == 0


def test_list_sources_sorted_and_distinct(store):
    provider = FakeEmbeddingProvider(dimension=16)
    store.add(_chunks_for("b.txt", ["x"], "h1"), provider.embed(["x"]))
    store.add(_chunks_for("a.txt", ["y"], "h2"), provider.embed(["y"]))
    assert store.list_sources() == ["a.txt", "b.txt"]


def test_get_source_hash(store):
    provider = FakeEmbeddingProvider(dimension=16)
    store.add(_chunks_for("doc1.txt", ["a"], file_hash="abc123"), provider.embed(["a"]))
    assert store.get_source_hash("doc1.txt") == "abc123"
    assert store.get_source_hash("inconnu.txt") is None


def test_embedding_model_roundtrip(store):
    assert store.get_embedding_model() is None
    store.set_embedding_model("nomic-embed-text")
    assert store.get_embedding_model() == "nomic-embed-text"


def test_iter_chunks(store):
    provider = FakeEmbeddingProvider(dimension=16)
    texts = ["a", "b", "c"]
    store.add(_chunks_for("doc1.txt", texts, "h1"), provider.embed(texts))
    chunks = list(store.iter_chunks())
    assert len(chunks) == 3
    assert [c.text for c in chunks] == texts
    assert all(c.source == "doc1.txt" for c in chunks)
    assert [c.index for c in chunks] == [0, 1, 2]


def test_clear(store):
    provider = FakeEmbeddingProvider(dimension=16)
    store.add(_chunks_for("doc1.txt", ["a"], "h1"), provider.embed(["a"]))
    store.set_embedding_model("m")
    store.clear()
    assert store.count() == 0
    assert store.list_sources() == []
    assert store.get_embedding_model() is None


def test_add_is_upsert(store):
    """Ré-ajouter le même id met à jour le texte au lieu de dupliquer."""
    provider = FakeEmbeddingProvider(dimension=16)
    store.add(_chunks_for("doc1.txt", ["ancien texte"], "h1"), provider.embed(["ancien"]))
    chunk = Chunk(
        id=Chunk.make_id("doc1.txt", None, 0),
        text="nouveau texte",
        source="doc1.txt",
        page=None,
        index=0,
        metadata={"file_hash": "h2"},
    )
    store.add([chunk], [provider.embed_query("nouveau")])
    assert store.count() == 1
    assert list(store.iter_chunks())[0].text == "nouveau texte"


def test_add_size_mismatch_rejected(store):
    provider = FakeEmbeddingProvider(dimension=16)
    with pytest.raises(ValueError):
        store.add(_chunks_for("doc1.txt", ["a"]), provider.embed(["a", "b"]))


def test_persistence(tmp_path):
    """Recréer le store sur le même dossier retrouve tout (persistance)."""
    provider = FakeEmbeddingProvider(dimension=16)
    path = tmp_path / "index"

    impls = ["simple"]
    try:
        pytest.importorskip("chromadb")
        impls.append("chroma")
    except pytest.skip.Exception:
        pass

    for impl in impls:
        writer = _make_store(impl, path)
        texts = ["texte persistant"]
        writer.add(_chunks_for("doc.txt", texts, "h9"), provider.embed(texts))
        writer.set_embedding_model("nomic-embed-text")
        if hasattr(writer, "close"):
            writer.close()

        reader = _make_store(impl, path)
        assert reader.count() == 1
        assert reader.list_sources() == ["doc.txt"]
        assert reader.get_embedding_model() == "nomic-embed-text"
        assert reader.get_source_hash("doc.txt") == "h9"
        results = reader.search(provider.embed_query("texte persistant"), top_k=1)
        assert results[0].chunk.text == "texte persistant"


def test_simple_store_usable_from_another_thread(tmp_path):
    """Regression : le conteneur est un singleton partagé entre les threads du
    serveur Django — la connexion doit rester utilisable depuis un thread
    différent de celui qui a créé le store."""
    store = SimpleVectorStore(tmp_path / "index")
    provider = FakeEmbeddingProvider(dimension=16)
    texts = ["texte inter-threads"]
    results: list = []

    def work() -> None:
        store.add(_chunks_for("doc1.txt", texts, "h1"), provider.embed(texts))
        results.append(store.search(provider.embed_query("inter-threads"), top_k=1))

    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    assert [r.chunk.text for r in results[0]] == texts
