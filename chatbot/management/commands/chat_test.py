"""Commande de test du LLM : `python manage.py chat_test "question" [--stream] [--system ...]`."""

from django.core.management.base import BaseCommand, CommandError

from rag_core.exceptions import LLMError
from rag_core.llm.factory import LLMFactory
from rag_core.models import ChatMessage
from rag_core.settings import get_settings


class Command(BaseCommand):
    """Interroge le LLM configuré (Ollama en local) et affiche la réponse."""

    help = "Interroge le LLM configuré (Ollama en local) et affiche la réponse."

    def add_arguments(self, parser) -> None:
        parser.add_argument("prompt", type=str, help="Question posée au modèle.")
        parser.add_argument(
            "--stream", action="store_true", help="Affiche la réponse en streaming."
        )
        parser.add_argument(
            "--system", type=str, default=None, help="Message system optionnel."
        )

    def handle(self, *args, **options) -> None:
        messages: list[ChatMessage] = []
        if options["system"]:
            messages.append(ChatMessage(role="system", content=options["system"]))
        messages.append(ChatMessage(role="user", content=options["prompt"]))

        llm = LLMFactory.create(get_settings())

        try:
            if options["stream"]:
                for fragment in llm.stream(messages):
                    self.stdout.write(fragment, ending="")
                    self.stdout.flush()
                self.stdout.write("")
            else:
                answer = llm.chat(messages)
                self.stdout.write(answer)
        except LLMError as exc:
            # Message lisible sans trace Python brute, code de sortie non nul.
            raise CommandError(str(exc)) from exc
