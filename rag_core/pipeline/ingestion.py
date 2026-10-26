"""Pipeline d'ingestion : charger → découper → embedder par lots → stocker."""

import hashlib
import logging
import time
from dataclasses import dataclass, replace
from pathlib import Path

from rag_core.chunking.base import Chunker
from rag_core.embeddings.base import EmbeddingProvider
from rag_core.exceptions import EmbeddingModelMismatchError, RagError
from rag_core.loaders.factory import LoaderFactory
from rag_core.models import Chunk
from rag_core.vectorstore.base import VectorStore

logger = logging.getLogger(__name__)

_HASH_BLOCK_SIZE = 1024 * 1024  # lecture du fichier par blocs de 1 Mo


@dataclass(frozen=True)
class IngestionReport:
    """Résultat d'une ingestion de fichier (≈ DTO de retour)."""

    source: str
    chunks_count: int
    skipped: bool = False
    error: str | None = None
    duration_seconds: float = 0.0


class IngestionPipeline:
    """Assemble loaders, chunker, embeddings et store.

    Ne connaît que des interfaces : aucune implémentation concrète.
    Le `Container` (ou les tests) choisit les implémentations.
    """

    def __init__(
        self,
        loader_factory: type[LoaderFactory],
        chunker: Chunker,
        embeddings: EmbeddingProvider,
        store: VectorStore,
        batch_size: int,
    ) -> None:
        self._loader_factory = loader_factory
        self._chunker = chunker
        self._embeddings = embeddings
        self._store = store
        self._batch_size = batch_size

    def ingest_file(self, path: Path, source: str | None = None, force: bool = False) -> (
        IngestionReport
    ):
        """Indexe un fichier ; les erreurs sont levées (pas de rapport d'erreur)."""
        started = time.perf_counter()
        source = source or path.name
        file_hash = self._hash_file(path)

        # 1. Garde-fou : ne pas mélanger deux modèles d'embeddings dans un index.
        indexed_model = self._store.get_embedding_model()
        if indexed_model is None:
            self._store.set_embedding_model(self._embeddings.model_name)
        elif indexed_model != self._embeddings.model_name:
            raise EmbeddingModelMismatchError(
                f"L'index a été construit avec le modèle d'embeddings "
                f"{indexed_model!r}, mais la configuration demande "
                f"{self._embeddings.model_name!r} : les scores seraient faux. "
                "Réindexez tout (commande ingest avec --reset)."
            )

        # 2. Fichier inchangé : on passe (idempotence).
        if not force and self._store.get_source_hash(source) == file_hash:
            logger.info("%s : inchangé, ingestion sautée.", source)
            return self._report(source, self._count_source(source), skipped=True, started=started)

        # 3. Charger et découper.
        documents = self._loader_factory.for_path(path).load(path, source=source)
        chunks: list[Chunk] = []
        for document in documents:
            chunks.extend(self._chunker.split(document))
        # Tracer le hash du fichier dans chaque chunk (détection des changements).
        chunks = [
            replace(chunk, metadata={**chunk.metadata, "file_hash": file_hash})
            for chunk in chunks
        ]

        # 4. Remplacer l'ancienne version (pas de doublons), puis embedder par lots.
        self._store.delete_by_source(source)
        vectors: list[list[float]] = []
        for start in range(0, len(chunks), self._batch_size):
            batch = chunks[start : start + self._batch_size]
            vectors.extend(self._embeddings.embed([chunk.text for chunk in batch]))
        if chunks:
            self._store.add(chunks, vectors)

        logger.info("%s : %d chunks indexés.", source, len(chunks))
        return self._report(source, len(chunks), started=started)

    def ingest_directory(self, path: Path, force: bool = False) -> list[IngestionReport]:
        """Indexe récursivement tous les fichiers supportés d'un dossier.

        Une erreur sur un fichier est capturée dans son rapport : le lot
        continue (contrairement à `ingest_file` qui lève).
        """
        path = Path(path)
        reports: list[IngestionReport] = []
        for file in sorted(path.rglob("*")):
            if not file.is_file():
                continue
            if not self._loader_factory.supports(file):
                logger.debug("%s : extension non supportée, ignoré.", file.name)
                continue
            started = time.perf_counter()
            try:
                reports.append(self.ingest_file(file, force=force))
            except RagError as exc:
                logger.error("%s : échec de l'ingestion (%s)", file.name, exc)
                reports.append(
                    IngestionReport(
                        source=file.name, chunks_count=0, error=str(exc),
                        duration_seconds=time.perf_counter() - started,
                    )
                )
            except OSError as exc:
                logger.error("%s : fichier illisible (%s)", file.name, exc)
                reports.append(
                    IngestionReport(
                        source=file.name, chunks_count=0, error=str(exc),
                        duration_seconds=time.perf_counter() - started,
                    )
                )
        return reports

    def remove_source(self, source: str) -> int:
        """Retire une source de l'index ; renvoie le nombre de chunks supprimés."""
        return self._store.delete_by_source(source)

    # -- Internes ---------------------------------------------------------------

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(_HASH_BLOCK_SIZE), b""):
                digest.update(block)
        return digest.hexdigest()

    def _count_source(self, source: str) -> int:
        return sum(1 for chunk in self._store.iter_chunks() if chunk.source == source)

    def _report(
        self,
        source: str,
        chunks_count: int,
        *,
        skipped: bool = False,
        started: float,
    ) -> IngestionReport:
        return IngestionReport(
            source=source,
            chunks_count=chunks_count,
            skipped=skipped,
            duration_seconds=time.perf_counter() - started,
        )
