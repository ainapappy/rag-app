"""Démonstration de similarité sémantique : `python manage.py semantic_demo [--query ...]`."""

import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from rag_core.embeddings.factory import EmbeddingFactory
from rag_core.exceptions import EmbeddingError, LLMError
from rag_core.models import Chunk
from rag_core.settings import get_settings
from rag_core.vectorstore.simple import SimpleVectorStore

SENTENCES = [
    "Le chat dort sur le canapé.",
    "Un félin se repose sur le sofa.",
    "La voiture roule sur l'autoroute.",
    "L'automobile file à grande vitesse sur la route.",
    "Le soleil brille dans le ciel bleu.",
    "Il fait beau et chaud aujourd'hui.",
    "Le chien joue dans le jardin.",
    "Un animal remue la queue dans la cour.",
]


class Command(BaseCommand):
    """Embed 8 phrases, affiche la matrice de similarité, puis recherche --query."""

    help = (
        "Calcule les embeddings de phrases de démonstration, affiche la matrice de "
        "similarité cosinus, puis (avec --query) recherche les phrases les plus proches."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--query",
            type=str,
            default=None,
            help="Requête à rechercher sémantiquement parmi les phrases.",
        )

    def handle(self, *args, **options) -> None:
        try:
            embeddings = EmbeddingFactory.create(get_settings())
            self.stdout.write(f"Modèle d'embeddings : {embeddings.model_name}")
            vectors = embeddings.embed(SENTENCES)
        except (EmbeddingError, LLMError) as exc:
            raise CommandError(str(exc)) from exc

        self._print_similarity_matrix(vectors)

        query = options["query"]
        if not query:
            return

        # Store temporaire (dans le dossier temp de l'OS), jetable.
        store_path = Path(tempfile.mkdtemp(prefix="rag_demo_"))
        store = SimpleVectorStore(store_path)
        chunks = [
            Chunk(
                id=Chunk.make_id("demo", None, i),
                text=sentence,
                source="demo",
                page=None,
                index=i,
            )
            for i, sentence in enumerate(SENTENCES)
        ]
        store.add(chunks, vectors)
        query_vector = embeddings.embed_query(query)
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f'Recherche : « {query} »'))
        for result in store.search(query_vector, top_k=3):
            self.stdout.write(f"  {result.score:.4f}  {result.chunk.text}")
        store.close()

    def _print_similarity_matrix(self, vectors: list[list[float]]) -> None:
        """Affiche la matrice 8x8 des similarités cosinus arrondies."""
        from rag_core.embeddings.similarity import cosine_similarity

        labels = [f"{s[:12]:<12}" for s in SENTENCES]
        self.stdout.write("")
        self.stdout.write("Matrice de similarité cosinus :")
        header = " " * 13 + "".join(f"{label[:6]:>7}" for label in labels)
        self.stdout.write(header)
        for i, _sentence in enumerate(SENTENCES):
            row = f"{labels[i][:12]:>12} |"
            for j in range(len(SENTENCES)):
                score = cosine_similarity(vectors[i], vectors[j])
                row += f"{score:>7.2f}"
            self.stdout.write(row)
