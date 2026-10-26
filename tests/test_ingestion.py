"""Tests du pipeline d'ingestion, de la commande ingest et du conteneur."""

import io

import pytest
from django.core.management import call_command

from rag_core.chunking.fixed_size import FixedSizeChunker
from rag_core.container import Container, get_container, reset_container
from rag_core.embeddings.fake import FakeEmbeddingProvider
from rag_core.exceptions import EmbeddingModelMismatchError
from rag_core.loaders.factory import LoaderFactory
from rag_core.pipeline.ingestion import IngestionPipeline
from rag_core.settings import Settings
from rag_core.vectorstore.simple import SimpleVectorStore


class CountingEmbeddings(FakeEmbeddingProvider):
    """Faux embeddings qui compte les appels à embed() (pour tester les lots)."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.embed_calls = 0

    def embed(self, texts):
        self.embed_calls += 1
        return super().embed(texts)


def _write(path, content: str):
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# ingest_file
# ---------------------------------------------------------------------------


def test_ingest_file_indexes_chunks(container, tmp_path):
    file = _write(tmp_path / "note.txt", "Voici une note de test avec du contenu.")
    report = container.ingestion_pipeline.ingest_file(file)
    assert report.error is None
    assert report.skipped is False
    assert report.chunks_count == 1
    assert container.store.count() == 1
    assert container.store.get_embedding_model() == "fake-embedding"
    assert container.store.get_source_hash("note.txt") is not None


def test_reingest_identical_is_skipped(container, tmp_path):
    file = _write(tmp_path / "note.txt", "Contenu stable.")
    pipeline = container.ingestion_pipeline
    pipeline.ingest_file(file)
    report = pipeline.ingest_file(file)
    assert report.skipped is True
    assert container.store.count() == 1  # pas de doublon


def test_force_reindexes_without_duplicates(container, tmp_path):
    file = _write(tmp_path / "note.txt", "Contenu stable.")
    pipeline = container.ingestion_pipeline
    pipeline.ingest_file(file)
    report = pipeline.ingest_file(file, force=True)
    assert report.skipped is False
    assert container.store.count() == 1


def test_modified_file_replaces_old_content(container, tmp_path):
    file = _write(tmp_path / "note.txt", "Ancien contenu unique : ABLE.")
    pipeline = container.ingestion_pipeline
    pipeline.ingest_file(file)
    _write(file, "Nouveau contenu unique : BAKER.")
    report = pipeline.ingest_file(file)
    assert report.skipped is False
    texts = " ".join(chunk.text for chunk in container.store.iter_chunks())
    assert "BAKER" in texts
    assert "ABLE" not in texts


def test_embedding_model_mismatch(container, tmp_path):
    file = _write(tmp_path / "note.txt", "Du contenu.")
    container.store.set_embedding_model("ancien-modele")
    with pytest.raises(EmbeddingModelMismatchError, match="--reset"):
        container.ingestion_pipeline.ingest_file(file)


def test_directory_continues_on_error(container, tmp_path):
    """Un fichier corrompu n'interrompt pas le lot : l'erreur est dans le rapport."""
    _write(tmp_path / "bon.txt", "Contenu valide.")
    (tmp_path / "casse.pdf").write_bytes(b"pas un pdf du tout")
    (tmp_path / "ignore.xyz").write_text("extension inconnue")  # ignoré, pas de rapport
    reports = container.ingestion_pipeline.ingest_directory(tmp_path)
    assert len(reports) == 2  # bon.txt + casse.pdf (ignore.xyz filtré)
    by_source = {report.source: report for report in reports}
    assert by_source["bon.txt"].error is None
    assert by_source["bon.txt"].chunks_count == 1
    assert by_source["casse.pdf"].error is not None
    assert container.store.list_sources() == ["bon.txt"]


def test_ingestion_embeds_by_batches(tmp_path, tmp_store):
    embeddings = CountingEmbeddings(dimension=16)
    chunker = FixedSizeChunker(chunk_size=20, overlap=5)
    pipeline = IngestionPipeline(LoaderFactory, chunker, embeddings, tmp_store, batch_size=2)
    text = " ".join(f"mot{i}.fin" for i in range(40))  # plusieurs chunks
    file = _write(tmp_path / "lot.txt", text)
    report = pipeline.ingest_file(file)
    assert report.chunks_count >= 5
    expected_calls = -(-report.chunks_count // 2)  # ceil(chunks / batch_size)
    assert embeddings.embed_calls == expected_calls
    assert tmp_store.count() == report.chunks_count


def test_remove_source(container, tmp_path):
    file = _write(tmp_path / "note.txt", "Contenu à retirer.")
    container.ingestion_pipeline.ingest_file(file)
    assert container.store.count() == 1
    removed = container.ingestion_pipeline.remove_source("note.txt")
    assert removed == 1
    assert container.store.count() == 0


# ---------------------------------------------------------------------------
# Commande ingest (via call_command)
# ---------------------------------------------------------------------------


def test_ingest_command_list_and_ingest(tmp_path):
    store_path = tmp_path / "index"
    docs = tmp_path / "docs"
    docs.mkdir()
    _write(docs / "doc1.txt", "Un document d'exemple à indexer.")

    import os

    from rag_core.settings import get_settings

    os.environ["VECTOR_STORE_PATH"] = str(store_path)
    get_settings.cache_clear()
    reset_container()
    try:
        out = io.StringIO()
        call_command("ingest", str(docs), stdout=out)
        output = out.getvalue()
        assert "doc1.txt" in output
        assert "OK" in output

        # Fichier inchangé : SAUTÉ au second passage.
        out = io.StringIO()
        call_command("ingest", str(docs), stdout=out)
        assert "SAUTÉ" in out.getvalue()

        # --list affiche les sources et le total.
        out = io.StringIO()
        call_command("ingest", "--list", stdout=out)
        assert "doc1.txt" in out.getvalue()
        assert "Total" in out.getvalue()
    finally:
        os.environ.pop("VECTOR_STORE_PATH", None)
        get_settings.cache_clear()
        reset_container()


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------


def test_container_lazy_and_cached(monkeypatch, tmp_path):
    monkeypatch.setenv("VECTOR_STORE_PATH", str(tmp_path / "idx"))
    container = Container(Settings(_env_file=None))
    first = container.llm
    assert container.llm is first  # mis en cache
    from rag_core.llm.openai_compatible import OpenAICompatibleLLM
    from rag_core.vectorstore.simple import SimpleVectorStore

    assert isinstance(first, OpenAICompatibleLLM)
    assert isinstance(container.store, SimpleVectorStore)


def test_container_uses_injected_fakes(container):
    assert container.llm.__class__.__name__ == "FakeLLM"
    assert container.embeddings.model_name == "fake-embedding"
    assert isinstance(container.store, SimpleVectorStore)


def test_container_lazy_creation():
    container = Container(Settings(_env_file=None))
    assert container._llm is None  # rien de construit à l'instanciation
    assert container._store is None


def test_get_container_cached_and_reset(monkeypatch, tmp_path):
    monkeypatch.setenv("VECTOR_STORE_PATH", str(tmp_path / "idx"))
    reset_container()
    first = get_container()
    assert get_container() is first
    reset_container()
    assert get_container() is not first
