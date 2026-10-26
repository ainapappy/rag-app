"""Pipeline RAG : retrieve → prompt → LLM, avec sources et honnêteté."""


from rag_core.models import Answer, ChatMessage, SearchResult, Source, StreamedAnswer
from rag_core.prompting.prompt_builder import PromptBuilder
from rag_core.retrieval.retriever import Retriever

# Message fixe quand rien n'a été trouvé : pas d'appel LLM dans ce cas.
NO_ANSWER_MESSAGE = "Je n'ai pas trouvé cette information dans les documents."

_EXCERPT_CHARS = 200


class RagPipeline:
    """Répond uniquement à partir des documents, en citant ses sources.

    `rewriter` est accepté pour l'injection future (réécriture de requête,
    phase 07) mais n'est pas encore utilisé.
    """

    def __init__(
        self, retriever: Retriever, prompt_builder: PromptBuilder, llm, rewriter=None
    ) -> None:
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._llm = llm
        self._rewriter = rewriter  # réservé à la phase 07 (non utilisé ici)

    def ask(self, question: str, history: tuple[ChatMessage, ...] = ()) -> Answer:
        """Réponse complète ; sans résultat, répond « introuvable » sans appeler le LLM."""
        results = self._retriever.retrieve(question)
        if not results:
            return Answer(text=NO_ANSWER_MESSAGE, sources=(), found=False)
        messages = self._prompt_builder.build(question, results, history)
        text = self._llm.chat(messages)
        return Answer(text=text, sources=self._build_sources(results), found=True)

    def ask_stream(
        self, question: str, history: tuple[ChatMessage, ...] = ()
    ) -> StreamedAnswer:
        """Réponse en streaming ; les sources sont disponibles avant les tokens."""
        results = self._retriever.retrieve(question)
        if not results:
            return StreamedAnswer(sources=(), found=False, tokens=iter([NO_ANSWER_MESSAGE]))
        messages = self._prompt_builder.build(question, results, history)
        return StreamedAnswer(
            sources=self._build_sources(results),
            found=True,
            tokens=self._llm.stream(messages),
        )

    @staticmethod
    def _build_sources(results: list[SearchResult]) -> tuple[Source, ...]:
        """Sources dédupliquées par (source, page), meilleur score conservé."""
        best: dict[tuple[str, int | None], SearchResult] = {}
        for result in results:
            key = (result.chunk.source, result.chunk.page)
            if key not in best or result.score > best[key].score:
                best[key] = result
        ordered = sorted(best.values(), key=lambda result: result.score, reverse=True)
        return tuple(
            Source(
                source=result.chunk.source,
                page=result.chunk.page,
                score=result.score,
                excerpt=result.chunk.text[:_EXCERPT_CHARS],
            )
            for result in ordered
        )
