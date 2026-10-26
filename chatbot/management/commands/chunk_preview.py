"""Aperçu de découpage : `python manage.py chunk_preview <fichier> [options]`."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from rag_core.chunking.fixed_size import FixedSizeChunker
from rag_core.chunking.paragraph import ParagraphChunker
from rag_core.exceptions import LoaderError, UnsupportedFileTypeError
from rag_core.loaders.factory import LoaderFactory
from rag_core.settings import get_settings


class Command(BaseCommand):
    """Charge un fichier, le découpe et affiche des statistiques de chunks."""

    help = (
        "Charge un fichier (.txt, .md, .pdf), le découpe en chunks et affiche "
        "le nombre de chunks, les longueurs min/moyenne/max et les 3 premiers chunks."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("path", type=str, help="Chemin du fichier à découper.")
        parser.add_argument(
            "--strategy",
            type=str,
            choices=["fixed", "paragraph"],
            default=None,
            help="Stratégie de découpage (défaut : CHUNKER_STRATEGY du .env).",
        )
        parser.add_argument(
            "--size", type=int, default=None, help="Taille max d'un chunk (défaut : .env)."
        )
        parser.add_argument(
            "--overlap", type=int, default=None, help="Chevauchement (défaut : .env)."
        )

    def handle(self, *args, **options) -> None:
        settings = get_settings()
        strategy = options["strategy"] or settings.chunker_strategy
        size = options["size"] or settings.chunk_size
        overlap = options["overlap"] or settings.chunk_overlap

        path = Path(options["path"])
        chunker = (
            FixedSizeChunker(chunk_size=size, overlap=overlap)
            if strategy == "fixed"
            else ParagraphChunker(max_size=size)
        )

        try:
            documents = LoaderFactory.for_path(path).load(path)
        except (UnsupportedFileTypeError, LoaderError) as exc:
            raise CommandError(str(exc)) from exc

        chunks = [chunk for document in documents for chunk in chunker.split(document)]
        if not chunks:
            raise CommandError(f"Aucun chunk produit à partir de {path.name}.")

        lengths = [len(chunk.text) for chunk in chunks]
        self.stdout.write(self.style.MIGRATE_HEADING(f"{path.name}"))
        self.stdout.write(
            f"Stratégie : {strategy} | pages : {len(documents)} | chunks : {len(chunks)} | "
            f"longueurs min/moy/max : {min(lengths)}/{sum(lengths) // len(lengths)}/{max(lengths)}"
        )

        self.stdout.write("")
        self.stdout.write("3 premiers chunks :")
        for chunk in chunks[:3]:
            preview = chunk.text[:200].replace("\n", " ")
            suffix = "…" if len(chunk.text) > 200 else ""
            page = chunk.page if chunk.page is not None else "-"
            self.stdout.write(f"\n[{chunk.index}] source={chunk.source} page={page} "
                              f"({chunk.metadata.get('chunk_chars')} caractères)")
            self.stdout.write(f"    {preview}{suffix}")
