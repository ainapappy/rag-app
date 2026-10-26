"""Crée une clé d'API : `python manage.py create_api_key <nom>`."""

from django.core.management.base import BaseCommand

from chatbot.models import ApiKey


class Command(BaseCommand):
    """Génère une clé d'API et l'affiche en clair une seule fois."""

    help = "Crée une clé d'API et l'affiche EN CLAIR UNE SEULE FOIS."

    def add_arguments(self, parser) -> None:
        parser.add_argument("name", type=str, help="Nom descriptif de la clé.")

    def handle(self, *args, **options) -> None:
        api_key, raw_key = ApiKey.generate(options["name"])
        self.stdout.write(self.style.WARNING(
            "Conservez cette clé maintenant : elle ne sera plus jamais affichée "
            "(seul son hash est stocké en base)."
        ))
        self.stdout.write("")
        self.stdout.write(raw_key)
        self.stdout.write("")
        self.stdout.write(f"Clé « {api_key.name} » créée (préfixe {api_key.prefix}…).")
