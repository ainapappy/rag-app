"""Tests de l'évaluateur, de BM25 et du retriever hybride (sans réseau)."""

import json

import pytest

from rag_core.embeddings.fake import FakeEmbeddingProvider
from rag_core.evaluation.evaluator import RagEvaluator
from rag_core.evaluation.models import EvalCase
from rag_core.models import Chunk
from rag_core.retrieval.bm25 import Bm25Index, tokenize
from rag_core.retrieval.hybrid import HybridRetriever
from rag_core.retrieval.retriever import Retriever
from rag_core.vectorstore.simple import SimpleVectorStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _store_with_docs(tmp_path) -> tuple[SimpleVectorStore, FakeEmbeddingProvider]:
    """Store avec deux sources ; textes exacts pour des scores déterministes."""
    store = SimpleVectorStore(tmp_path / "index")
    embeddings = FakeEmbeddingProvider(dimension=16)
    texts = {
        "a.txt": [
            "La politique de congés accorde vingt-cinq jours par an.",
            "Le report de congés est limité huit jours avant mars.",
        ],
        "b.txt": [
            "La vanille de Madagascar est cultivée dans la région du Sava.",
            "L'échaudage des gousses se fait soixante-cinq degrés.",
        ],
    }
    for source, source_texts in texts.items():
        chunks = [
            Chunk(
                id=Chunk.make_id(source, None, i),
                text=text,
                source=source,
                index=i,
            )
            for i, text in enumerate(source_texts)
        ]
        store.add(chunks, embeddings.embed(source_texts))
    return store, embeddings


def _case(**overrides) -> EvalCase:
    base = {
        "id": "q01",
        "question": "La politique de congés accorde vingt-cinq jours par an.",
        "expected_source": "a.txt",
        "expected_page": None,
        "expected_keywords": ("vingt-cinq",),
        "should_answer": True,
    }
    base.update(overrides)
    return EvalCase(**base)


# ---------------------------------------------------------------------------
# RagEvaluator
# ---------------------------------------------------------------------------


def test_evaluator_hits_relevant_source(tmp_path):
    store, embeddings = _store_with_docs(tmp_path)
    evaluator = RagEvaluator(Retriever(embeddings, store, top_k=3, min_score=1.0))
    report = evaluator.evaluate([_case()])
    assert report.hit_at_k == pytest.approx(1.0)
    assert report.mrr == pytest.approx(1.0)
    result = report.cases[0]
    assert result.hit is True
    assert result.rank == 1


def test_evaluator_measures_correct_refusal(tmp_path):
    """Question hors sujet avec min_score=1.0 : aucun résultat → bon refus."""
    store, embeddings = _store_with_docs(tmp_path)
    evaluator = RagEvaluator(Retriever(embeddings, store, top_k=3, min_score=1.0))
    report = evaluator.evaluate([
        _case(id="q99", question="texte totalement absent des documents",
              expected_source=None, should_answer=False),
    ])
    assert report.no_answer_rate == pytest.approx(1.0)
    assert report.cases[0].no_answer_correct is True


def test_evaluator_detects_missed_refusal(tmp_path):
    """Le système répond alors qu'il ne devrait pas : taux de refus à 0."""
    store, embeddings = _store_with_docs(tmp_path)
    evaluator = RagEvaluator(Retriever(embeddings, store, top_k=3, min_score=0.0))
    report = evaluator.evaluate([
        _case(id="q99", question="La politique de congés accorde vingt-cinq jours par an.",
              expected_source=None, should_answer=False),
    ])
    assert report.no_answer_rate == pytest.approx(0.0)


def test_evaluator_with_pipeline_measures_keyword_recall(tmp_path):
    class StubPipeline:
        def ask(self, question):
            from rag_core.models import Answer

            return Answer(text="Le texte parle de vanille et de Sava.", sources=(), found=True)

    store, embeddings = _store_with_docs(tmp_path)
    pipeline = StubPipeline()
    evaluator = RagEvaluator(
        Retriever(embeddings, store, top_k=3, min_score=1.0), pipeline=pipeline
    )
    case = _case(
        question="La vanille de Madagascar est cultivée dans la région du Sava.",
        expected_source="b.txt",
        expected_keywords=("vanille", "Sava"),
    )
    report = evaluator.evaluate([case])
    assert report.keyword_recall == pytest.approx(1.0)
    assert report.cases[0].answer.startswith("Le texte parle")


def test_evaluator_mixed_cases_aggregation(tmp_path):
    store, embeddings = _store_with_docs(tmp_path)
    evaluator = RagEvaluator(Retriever(embeddings, store, top_k=3, min_score=1.0))
    report = evaluator.evaluate([
        _case(id="q_hit", question="La politique de congés accorde vingt-cinq jours par an."),
        _case(id="q_miss", question="texte totalement absent",
              expected_source="b.txt"),
    ])
    assert report.hit_at_k == pytest.approx(0.5)  # 1 hit sur 2 questions attendues
    assert report.mrr == pytest.approx(0.5)
    assert report.no_answer_rate is None  # aucun cas « sans réponse »


# ---------------------------------------------------------------------------
# BM25
# ---------------------------------------------------------------------------


def test_tokenize_strips_accents_and_lowercases():
    assert tokenize("ÉCHAUDAGE élevage") == ["echaudage", "elevage"]


def test_bm25_ranks_exact_rare_word_first(tmp_path):
    chunks = [
        Chunk(id="c1", text="Le chat dort sur le canapé.", source="a", index=0),
        Chunk(
            id="c2", text="L'échaudage de la vanille à soixante-cinq degrés.",
            source="b", index=1,
        ),
        Chunk(id="c3", text="Le chat et le chien jouent au jardin.", source="c", index=2),
    ]
    index = Bm25Index(chunks)
    results = index.search("échaudage vanille", top_k=3)
    assert results[0][0].id == "c2"
    # accents ignorés : « echaudage » trouve le chunk 2 aussi
    results_ascii = index.search("echaudage", top_k=3)
    assert results_ascii[0][0].id == "c2"


def test_bm25_empty_index_returns_nothing():
    assert Bm25Index([]).search("anything", top_k=3) == []


def test_bm25_from_store(tmp_path):
    store, _ = _store_with_docs(tmp_path)
    index = Bm25Index.from_store(store)
    results = index.search("conges vingt-cinq", top_k=1)
    assert results[0][0].source == "a.txt"


# ---------------------------------------------------------------------------
# HybridRetriever
# ---------------------------------------------------------------------------


def test_hybrid_respects_retriever_interface(tmp_path):
    store, embeddings = _store_with_docs(tmp_path)
    hybrid = HybridRetriever(
        embeddings, store, Bm25Index.from_store(store), top_k=3, min_score=1.0
    )
    assert hybrid.top_k == 3
    assert hybrid.min_score == 1.0
    results = hybrid.retrieve(
        "La politique de congés accorde vingt-cinq jours par an."
    )
    assert results and hasattr(results[0], "chunk") and hasattr(results[0], "score")


def test_hybrid_rrf_boosts_chunk_good_in_both_rankings(tmp_path):
    """Un chunk bien classé en vectoriel ET en BM25 remonte en tête de la fusion."""
    store, embeddings = _store_with_docs(tmp_path)
    bm25 = Bm25Index.from_store(store)
    query = "La politique de congés accorde vingt-cinq jours par an."

    vector_only = Retriever(embeddings, store, top_k=2, min_score=0.0)
    vector_top = vector_only.retrieve(query)[0].chunk.id
    bm25_top = bm25.search(query, top_k=2)[0][0].id

    hybrid = HybridRetriever(embeddings, store, bm25, top_k=2, min_score=0.0)
    fused_top = hybrid.retrieve(query)[0].chunk.id
    # Si les deux méthodes d'accord sur le meilleur, la fusion le confirme.
    if vector_top == bm25_top:
        assert fused_top == vector_top
    else:
        # Sinon le chunk présent dans les deux listes doit gagner.
        assert fused_top in {vector_top, bm25_top}


def test_hybrid_min_score_filters_vector_results(tmp_path):
    """min_score=1.0 : ne passent que les correspondances exactes (vectoriel)."""
    store, embeddings = _store_with_docs(tmp_path)
    hybrid = HybridRetriever(
        embeddings, store, Bm25Index.from_store(store), top_k=3, min_score=1.0
    )
    results = hybrid.retrieve("La politique de congés accorde vingt-cinq jours par an.")
    assert all(result.score > 0 for result in results)
    assert len(results) <= 3


# ---------------------------------------------------------------------------
# Commande eval_rag (sans LLM, conteneur factice)
# ---------------------------------------------------------------------------


def test_eval_rag_command_runs(tmp_path, monkeypatch, capsys):
    """La commande s'exécute sur un store factice et affiche les métriques."""
    from django.core.management import call_command

    import rag_core.container as container_module
    from rag_core.settings import Settings
    from tests.conftest import FakeChatContainer

    store, embeddings = _store_with_docs(tmp_path / "store")
    container = FakeChatContainer(RecordingPipelineStub())
    container.store = store
    container.embeddings = embeddings
    monkeypatch.setattr(container_module, "get_container", lambda: container)
    monkeypatch.setattr("chatbot.management.commands.eval_rag.get_settings",
                        lambda: Settings(_env_file=None))

    questions = tmp_path / "questions.json"
    questions.write_text(json.dumps([
        {"id": "q01", "question": "La politique de congés accorde vingt-cinq jours par an.",
         "expected_source": "a.txt", "expected_page": None,
         "expected_keywords": [], "should_answer": True},
    ]), encoding="utf-8")

    call_command("eval_rag", file=str(questions), output=str(tmp_path / "report.json"))
    output = capsys.readouterr().out
    assert "Hit@k" in output
    assert "MRR" in output
    assert (tmp_path / "report.json").exists()


class RecordingPipelineStub:
    """Pipeline minimal (non appelé sans --with-llm)."""

    def ask(self, question, history=()):
        raise AssertionError("le pipeline ne doit pas être appelé sans --with-llm")
