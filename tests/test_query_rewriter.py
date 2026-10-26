"""Tests du QueryRewriter : pas d'appel inutile, reformulation, repli d'erreur."""

from rag_core.exceptions import LLMError
from rag_core.models import ChatMessage
from rag_core.prompting.query_rewriter import QueryRewriter


def test_empty_history_returns_question_without_llm_call(fake_llm):
    rewriter = QueryRewriter(fake_llm)
    assert rewriter.rewrite("Question directe ?") == "Question directe ?"
    assert fake_llm.calls == []


def test_rewrites_follow_up_question_with_history(fake_llm):
    fake_llm.responses = ['Quelle est la politique de congés maladie ?']
    rewriter = QueryRewriter(fake_llm)
    history = (ChatMessage(role="user", content="Combien de jours de congés payés ?"),)
    result = rewriter.rewrite("et pour les congés maladie ?", history)
    assert result == "Quelle est la politique de congés maladie ?"
    assert len(fake_llm.calls) == 1  # un seul appel LLM


def test_rewrite_strips_quotes_and_whitespace(fake_llm):
    fake_llm.responses = ['  " Une question reformulée ? "  \n']
    rewriter = QueryRewriter(fake_llm)
    history = (ChatMessage(role="user", content="Bonjour"),)
    assert rewriter.rewrite("et donc ?", history) == "Une question reformulée ?"


def test_empty_rewritten_answer_falls_back(fake_llm):
    fake_llm.responses = ["   "]
    rewriter = QueryRewriter(fake_llm)
    history = (ChatMessage(role="user", content="Bonjour"),)
    assert rewriter.rewrite("ma question", history) == "ma question"


def test_llm_error_falls_back_to_original_question():
    class FailingLLM:
        def chat(self, messages):
            raise LLMError("Ollama injoignable")

        def stream(self, messages):
            raise LLMError("Ollama injoignable")

    rewriter = QueryRewriter(FailingLLM())
    history = (ChatMessage(role="user", content="Bonjour"),)
    assert rewriter.rewrite("ma question", history) == "ma question"
