"""Indexation de documents : `python manage.py ingest <chemin> [options]`."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from rag_core.exceptions import RagError


class Command(BaseCommand):
    """Indexe un fichier ou un dossier dans le magasin vectoriel (idempotent)."""

    help = (
        "Charge, découpe et indexe les fichiers supportés (.txt, .md, .pdf) du "
        "chemin donné. Idempotent : les fichiers inchangés sont sautés."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "path", nargs="?", default=None, help="Fichier ou dossier à indexer."
        )
        parser.add_argument(
            "--force", action="store_true", help="Réindexe même si le fichier est inchangé."
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Vide l'index avant (obligatoire après changement d'EMBED_MODEL).",
        )
        parser.add_argument(
            "--list", action="store_true", help="Affiche les sources indexées puis quitte."
        )

    def handle(self, *args, **options) -> None:
        # Import tardif : après django.setup(), rag_core reste indépendant.
        from rag_core.container import get_container

        container = get_container()
        store = container.store

        if options["reset"]:
            store.clear()
            self.stdout.write(self.style.WARNING("Index vidé (modèle d'embeddings réinitialisé)."))

        if options["list"]:
            self._list_sources(store)
            return

        path = options["path"]
        if not path:
            raise CommandError("Indiquez un chemin à indexer, ou --list pour l'état de l'index.")

        target = Path(path)
        try:
            pipeline = container.ingestion_pipeline
            if target.is_dir():
                reports = pipeline.ingest_directory(target, force=options["force"])
            else:
                reports = [pipeline.ingest_file(target, force=options["force"])]
        except RagError as exc:
            raise CommandError(str(exc)) from exc

        self._print_reports(reports)
        errors = sum(1 for report in reports if report.error)
        if errors:
            raise CommandError(f"{errors} fichier(s) en erreur pendant l'ingestion.")

    def _list_sources(self, store) -> None:
        sources = store.list_sources()
        if not sources:
            self.stdout.write("Index vide.")
            return
        counts = {source: 0 for source in sources}
        for chunk in store.iter_chunks():
            counts[chunk.source] += 1
        self.stdout.write(self.style.MIGRATE_HEADING("Sources indexées :"))
        for source in sources:
            self.stdout.write(f"  {source:<40} {counts[source]:>5} chunks")
        self.stdout.write(f"\nTotal : {store.count()} chunks, {len(sources)} source(s).")

    def _print_reports(self, reports) -> None:
        self.stdout.write("")
        self.stdout.write(
            f"{'Source':<40} {'Chunks':>7}  {'Statut':<10} {'Durée':>8}"
        )
        self.stdout.write("-" * 70)
        for report in reports:
            status = "ERREUR" if report.error else ("SAUTÉ" if report.skipped else "OK")
            line = (
                f"{report.source[:40]:<40} {report.chunks_count:>7}  {status:<10} "
                f"{report.duration_seconds:>7.2f}s"
            )
            self.stdout.write(line)
            if report.error:
                self.stdout.write(self.style.ERROR(f"    -> {report.error}"))
        indexed = sum(1 for r in reports if not r.skipped and not r.error)
        skipped = sum(1 for r in reports if r.skipped)
        self.stdout.write(
            f"\nRésumé : {indexed} indexé(s), {skipped} sauté(s), "
            f"{sum(r.chunks_count for r in reports)} chunks au total."
        )
