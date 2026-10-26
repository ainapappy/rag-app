"""Évalue la qualité du RAG : `python manage.py eval_rag [options]`."""

import json
import tempfile
import time
from pathlib import Path

from django.core.management.base import BaseCommand

from rag_core.chunking.fixed_size import FixedSizeChunker
from rag_core.evaluation.dataset import EvalDataset
from rag_core.evaluation.evaluator import RagEvaluator
from rag_core.evaluation.judge import FaithfulnessJudge
from rag_core.loaders.factory import LoaderFactory
from rag_core.pipeline.ingestion import IngestionPipeline
from rag_core.retrieval.bm25 import Bm25Index
from rag_core.retrieval.hybrid import HybridRetriever
from rag_core.retrieval.retriever import Retriever
from rag_core.settings import get_settings
from rag_core.vectorstore.simple import SimpleVectorStore

# Grille du sweep (produit cartésien des valeurs).
SWEEP_GRID = {
    "chunk_size": [400, 700, 1000],
    "overlap": [50, 100],
    "top_k": [3, 4, 6],
}


class Command(BaseCommand):
    """Mesure Hit@k, MRR, taux de bons refus (et plus avec --with-llm/--judge)."""

    help = "Évalue la qualité de récupération et de réponse du RAG sur un jeu de questions."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--file", default="eval/questions.json", help="Jeu de questions.")
        parser.add_argument("--top-k", type=int, default=None, dest="top_k")
        parser.add_argument("--min-score", type=float, default=None, dest="min_score")
        parser.add_argument(
            "--retriever", choices=["vector", "hybrid"], default=None, dest="retriever"
        )
        parser.add_argument("--with-llm", action="store_true", dest="with_llm",
                            help="Mesure aussi le rappel des mots-clés sur les réponses générées.")
        parser.add_argument("--judge", action="store_true",
                            help="Juge de fidélité LLM (mesure indicative).")
        parser.add_argument("--output", default=None,
                            help="Chemin d'un rapport JSON (défaut : aucun).")
        parser.add_argument("--sweep", action="store_true",
                            help="Teste une grille de réglages sur un index temporaire.")

    def handle(self, *args, **options) -> None:
        from rag_core import container as container_module

        container = container_module.get_container()
        settings = get_settings()
        top_k = options["top_k"] or settings.top_k
        min_score = (
            options["min_score"] if options["min_score"] is not None else settings.min_score
        )
        retriever_kind = options["retriever"] or settings.retriever
        cases = EvalDataset.load(Path(options["file"]))

        if options["sweep"]:
            self._run_sweep(container, cases)
            return

        retriever = self._build_retriever(container, retriever_kind, top_k, min_score)
        pipeline = container.rag_pipeline if options["with_llm"] else None
        judge = FaithfulnessJudge(container.llm) if options["judge"] else None

        report = RagEvaluator(retriever, pipeline=pipeline, judge=judge).evaluate(cases)
        self._print_report(report, retriever_kind, top_k, min_score)

        if options["output"]:
            path = Path(options["output"])
            path.parent.mkdir(parents=True, exist_ok=True)
            from dataclasses import asdict

            path.write_text(
                json.dumps(asdict(report), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.stdout.write(f"Rapport écrit : {path}")

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_retriever(container, kind: str, top_k: int, min_score: float):
        if kind == "hybrid":
            bm25 = Bm25Index.from_store(container.store)
            return HybridRetriever(
                container.embeddings, container.store, bm25, top_k, min_score
            )
        return Retriever(container.embeddings, container.store, top_k, min_score)

    # ------------------------------------------------------------------
    # Affichage
    # ------------------------------------------------------------------

    def _print_report(self, report, kind: str, top_k: int, min_score: float) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Évaluation (retriever={kind}, top_k={top_k}, min_score={min_score})"
        ))
        self.stdout.write(f"{'ID':<6} {'':<2} {'Rang':>4}  {'Source attendue':<24} Question")
        self.stdout.write("-" * 90)
        for result in report.cases:
            correct = result.no_answer_correct
            mark = "OK" if correct else "!!"
            rank = result.rank if result.rank is not None else "-"
            expected = result.case.expected_source or "(aucune réponse attendue)"
            self.stdout.write(
                f"{result.case.id:<6} {mark:<2} {str(rank):>4}  {expected:<24} "
                f"{result.case.question[:45]}"
            )
        self.stdout.write("")
        self.stdout.write(f"Hit@k        : {report.hit_at_k:.2%}")
        self.stdout.write(f"MRR          : {report.mrr:.3f}")
        if report.no_answer_rate is not None:
            self.stdout.write(f"Bons refus   : {report.no_answer_rate:.2%}")
        if report.keyword_recall is not None:
            self.stdout.write(f"Recall kwd   : {report.keyword_recall:.2%}")
        if report.faithfulness is not None:
            self.stdout.write(f"Fidélité     : {report.faithfulness:.2%} (indicatif)")

    # ------------------------------------------------------------------
    # Sweep : grille de réglages sur un index TEMPORAIRE (jamais data/index)
    # ------------------------------------------------------------------

    def _run_sweep(self, container, cases) -> None:
        results: list[dict] = []
        settings = get_settings()
        combinations = [
            (chunk_size, overlap, top_k)
            for chunk_size in SWEEP_GRID["chunk_size"]
            for overlap in SWEEP_GRID["overlap"]
            for top_k in SWEEP_GRID["top_k"]
        ]
        total = len(combinations)
        for index, (chunk_size, overlap, top_k) in enumerate(combinations, start=1):
            started = time.perf_counter()
            with tempfile.TemporaryDirectory(prefix="rag_sweep_") as tmp:
                store = SimpleVectorStore(Path(tmp) / "index")
                pipeline = IngestionPipeline(
                    loader_factory=LoaderFactory,
                    chunker=FixedSizeChunker(chunk_size=chunk_size, overlap=overlap),
                    embeddings=container.embeddings,
                    store=store,
                    batch_size=settings.embed_batch_size,
                )
                pipeline.ingest_directory(Path("docs"))
                retriever = Retriever(
                    container.embeddings, store, top_k, settings.min_score
                )
                report = RagEvaluator(retriever).evaluate(cases)
                store.close()  # libère le SQLite : sinon Windows bloque le cleanup
            results.append({
                "chunk_size": chunk_size,
                "overlap": overlap,
                "top_k": top_k,
                "hit_at_k": report.hit_at_k,
                "mrr": report.mrr,
                "no_answer_rate": report.no_answer_rate,
                "seconds": time.perf_counter() - started,
            })
            self.stdout.write(f"[{index}/{total}] chunk={chunk_size} overlap={overlap} "
                              f"top_k={top_k} -> MRR {report.mrr:.3f}")

        results.sort(key=lambda row: row["mrr"], reverse=True)
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            "Sweep (trié par MRR) — index temporaire, data/index intact"
        ))
        header = (
            f"{'chunk':>6} {'overlap':>8} {'top_k':>6} "
            f"{'Hit@k':>7} {'MRR':>7} {'Refus':>7} {'Durée':>7}"
        )
        self.stdout.write(header)
        for row in results:
            refus = f"{row['no_answer_rate']:.0%}" if row["no_answer_rate"] is not None else "-"
            self.stdout.write(
                f"{row['chunk_size']:>6} {row['overlap']:>8} {row['top_k']:>6} "
                f"{row['hit_at_k']:>7.0%} {row['mrr']:>7.3f} {refus:>7} "
                f"{row['seconds']:>6.1f}s"
            )
        best = results[0]
        self.stdout.write(
            f"\nMeilleure combinaison : chunk={best['chunk_size']} "
            f"overlap={best['overlap']} top_k={best['top_k']} (MRR {best['mrr']:.3f})"
        )
