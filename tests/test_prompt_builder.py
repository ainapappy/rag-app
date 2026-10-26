"""Tests du PromptBuilder : instructions, numérotation, historique, troncature."""

from rag_core.models import ChatMessage, Chunk, SearchResult
from rag_core.prompting.prompt_builder import PromptBuilder


def _result(text: str, source: str = "doc.pdf", page: int | None = 1, score: float = 0.9):
    chunk = Chunk(id=Chunk.make_id(source, page, 0), text=text, source=source, page=page)
    return SearchResult(chunk=chunk, score=score)


def test_system_message_forbids_leaving_context():
    messages = PromptBuilder().build("Question ?", [_result("Contenu.")])
    system = messages[0]
    assert system.role == "system"
    assert "UNIQUEMENT" in system.content
    assert "n'invente jamais" in system.content.lower() or "N'invente jamais" in system.content


def test_context_is_numbered_with_source_and_page():
    builder = PromptBuilder()
    messages = builder.build("Question ?", [_result("Contenu A."), _result("Contenu B.", page=3)])
    user = messages[-1].content
    assert "[1] (doc.pdf, page 1)" in user
    assert "[2] (doc.pdf, page 3)" in user
    assert "Contenu A." in user and "Contenu B." in user
    assert "Question : ?" in user or "Question : Question ?" in user


def test_history_comes_before_final_question():
    history = (
        ChatMessage(role="user", content="Première question"),
        ChatMessage(role="assistant", content="Première réponse"),
    )
    messages = PromptBuilder().build("Question finale", [_result("Contenu.")], history=history)
    roles = [message.role for message in messages]
    assert roles == ["system", "user", "assistant", "user"]
    assert messages[1].content == "Première question"
    assert "Question finale" in messages[-1].content


def test_context_is_truncated_to_max_chars():
    builder = PromptBuilder(max_context_chars=120)
    big_text = "x" * 500
    messages = builder.build("Q", [_result(big_text, page=1), _result("y" * 500, page=2)])
    user = messages[-1].content
    # Le contexte (texte + en-têtes + question) tient dans ~max_context_chars.
    assert user.index("Question :") <= 120 + len("Question : Q") + 50
    assert "…" in user or "y" * 500 not in user  # au moins un chunk tronqué/écarté


def test_empty_results_yield_placeholder():
    messages = PromptBuilder().build("Q", [])
    assert "aucun document fourni" in messages[-1].content
