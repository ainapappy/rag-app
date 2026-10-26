"""Tests du pipeline RAG : honnêteté, sources dédupliquées, streaming."""

import pytest

from rag_core.models import Chunk, SearchResult
from rag_core.pipeline.rag import NO_ANSWER_MESSAGE, RagPipeline
from rag_core.prompting.prompt_builder import PromptBuilder


class StubRetriever:
    """Retriever factice qui renvoie des résultats préparés (unitaire pur)."""

    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results
        self.queries: list[str] = []

    def retrieve(self, query: str) -> list[SearchResult]:
        self.queries.append(query)
        return self.results


def _result(text: str, source: str, page: int | None, score: float) -> SearchResult:
    chunk = Chunk(id=Chunk.make_id(source, page, 0), text=text, source=source, page=page)
    return SearchResult(chunk=chunk, score=score)


def test_ask_with_relevant_context_calls_llm_once(container):
    retriever = StubRetriever([_result("Il y a 25 jours de congés.", "conges.txt", 1, 0.95)])
    pipeline = RagPipeline(retriever, PromptBuilder(), container.llm)
    answer = pipeline.ask("Combien de jours de congés ?")
    assert answer.found is True
    assert answer.text == "Réponse par défaut du faux LLM."
    assert len(container.llm.calls) == 1
    assert answer.sources[0].source == "conges.txt"
    assert answer.sources[0].page == 1


def test_ask_without_result_skips_llm(container):
    retriever = StubRetriever([])
    pipeline = RagPipeline(retriever, PromptBuilder(), container.llm)
    answer = pipeline.ask("Quelle est la capitale de l'Australie ?")
    assert answer.found is False
    assert answer.text == NO_ANSWER_MESSAGE
    assert answer.sources == ()
    assert container.llm.calls == []  # le LLM n'a jamais été appelé


def test_sources_deduplicated_by_source_and_page(container):
    results = [
        _result("extrait un", "doc.pdf", 1, 0.80),
        _result("extrait deux (meilleur)", "doc.pdf", 1, 0.90),  # même (source, page)
        _result("autre page", "doc.pdf", 2, 0.70),
    ]
    retriever = StubRetriever(results)
    pipeline = RagPipeline(retriever, PromptBuilder(), container.llm)
    answer = pipeline.ask("question")
    assert len(answer.sources) == 2
    # Meilleur score conservé pour la paire dédupliquée.
    scores = {source.page: source.score for source in answer.sources}
    assert scores[1] == pytest.approx(0.90)
    assert scores[2] == pytest.approx(0.70)
    # Tri décroissant par score.
    assert answer.sources[0].score >= answer.sources[1].score


def test_ask_stream_yields_tokens_and_sources(container):
    container.llm.responses = ["un deux trois"]
    retriever = StubRetriever([_result("contexte pertinent", "doc.txt", 1, 0.9)])
    pipeline = RagPipeline(retriever, PromptBuilder(), container.llm)
    answer = pipeline.ask_stream("question")
    # Sources disponibles immédiatement, avant consommation des tokens.
    assert answer.found is True
    assert answer.sources[0].source == "doc.txt"
    fragments = list(answer.tokens)
    assert len(fragments) > 1  # bien découpé pour le streaming
    assert "".join(fragments) == "un deux trois"


def test_ask_stream_without_result_produces_no_answer_message(container):
    retriever = StubRetriever([])
    pipeline = RagPipeline(retriever, PromptBuilder(), container.llm)
    answer = pipeline.ask_stream("question hors sujet")
    assert answer.found is False
    assert list(answer.tokens) == [NO_ANSWER_MESSAGE]
    assert container.llm.calls == []


def test_ask_uses_history(container):
    from rag_core.models import ChatMessage

    retriever = StubRetriever([_result("contexte", "doc.txt", None, 0.9)])
    pipeline = RagPipeline(retriever, PromptBuilder(), container.llm)
    history = (ChatMessage(role="user", content="avant"),)
    pipeline.ask("question", history=history)
    sent_messages = container.llm.calls[0]
    assert sent_messages[1].content == "avant"  # historique inséré avant la question


def test_rag_pipeline_with_real_retriever_and_empty_store(container):
    """Store vide : le retriever ne renvoie rien → « introuvable » sans LLM."""
    pipeline = container.rag_pipeline
    answer = pipeline.ask("n'importe quelle question")
    assert answer.found is False
    assert answer.text == NO_ANSWER_MESSAGE


# ---------------------------------------------------------------------------
# Test d'intégration réel (pytest -m integration) : index + Ollama requis
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_real_rag_on_holidays_policy():
    """Question réelle sur politique_conges.txt (indexez docs/ avant)."""
    from rag_core.container import get_container

    pipeline = get_container().rag_pipeline
    answer = pipeline.ask("Combien de jours de congés payés par an ?")
    if not answer.found:
        pytest.skip("Index vide ou seuil trop haut : lancez `python manage.py ingest docs/`.")
    assert "25" in answer.text
    assert any(source.source == "politique_conges.txt" for source in answer.sources)
