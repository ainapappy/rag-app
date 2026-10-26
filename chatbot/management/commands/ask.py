"""Question sur les documents : `python manage.py ask "question" [options]`."""

from django.core.management.base import BaseCommand, CommandError

from rag_core.exceptions import LLMError
from rag_core.pipeline.rag import RagPipeline
from rag_core.retrieval.retriever import Retriever
from rag_core.settings import get_settings


class Command(BaseCommand):
    """Répond uniquement à partir des documents indexés, avec sources."""

    help = (
        "Pose une question au pipeline RAG : recherche les chunks pertinents "
        "puis interroge le LLM avec ce seul contexte. Affiche la réponse et "
        "les sources (fichier, page, score)."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("question", type=str, help="Question posée.")
        parser.add_argument(
            "--stream", action="store_true", help="Affiche la réponse en streaming."
        )
        parser.add_argument(
            "--top-k", type=int, default=None, dest="top_k",
            help="Nombre de chunks retrouvés (surcharge TOP_K du .env).",
        )
        parser.add_argument(
            "--min-score", type=float, default=None, dest="min_score",
            help="Score minimal (surcharge MIN_SCORE du .env).",
        )
        parser.add_argument(
            "--show-context", action="store_true", dest="show_context",
            help="Affiche aussi les chunks retrouvés avant la réponse.",
        )

    def handle(self, *args, **options) -> None:
        from rag_core.container import get_container

        settings = get_settings()
        container = get_container()

        # Options d'expérimentation : surchargent TOP_K / MIN_SCORE du .env.
        top_k = options["top_k"] or settings.top_k
        min_score = (
            options["min_score"] if options["min_score"] is not None else settings.min_score
        )
        retriever = Retriever(container.embeddings, container.store, top_k, min_score)
        pipeline = RagPipeline(retriever, container.prompt_builder, container.llm)

        if options["show_context"]:
            self._show_context(retriever, options["question"])

        try:
            if options["stream"]:
                answer = pipeline.ask_stream(options["question"])
                if answer.found:
                    self.stdout.write("Sources :")
                    for i, source in enumerate(answer.sources, start=1):
                        page = source.page if source.page is not None else "-"
                        self.stdout.write(f"  [{i}] {source.source} (page {page}, "
                                          f"score {source.score:.3f})")
                self.stdout.write("")
                for token in answer.tokens:
                    self.stdout.write(token, ending="")
                    self.stdout.flush()
                self.stdout.write("")
            else:
                answer = pipeline.ask(options["question"])
                self.stdout.write(answer.text)
                if answer.sources:
                    self.stdout.write("")
                    self.stdout.write("Sources :")
                    for i, source in enumerate(answer.sources, start=1):
                        page = source.page if source.page is not None else "-"
                        self.stdout.write(
                            f"  [{i}] {source.source} (page {page}, score {source.score:.3f})"
                        )
        except LLMError as exc:
            raise CommandError(str(exc)) from exc

    def _show_context(self, retriever, question: str) -> None:
        """Affiche les chunks que le retriever renvoie (debug / expérimentation)."""
        results = retriever.retrieve(question)
        self.stdout.write(self.style.MIGRATE_HEADING(f"Contexte ({len(results)} chunks) :"))
        for i, result in enumerate(results, start=1):
            page = result.chunk.page if result.chunk.page is not None else "-"
            preview = result.chunk.text[:150].replace("\n", " ")
            self.stdout.write(
                f"\n[{i}] {result.chunk.source} (page {page}, score {result.score:.3f})"
            )
            self.stdout.write(f"    {preview}…")
        self.stdout.write("")
