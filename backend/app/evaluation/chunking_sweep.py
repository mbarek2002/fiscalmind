from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass

import mlflow
import pandas as pd
from qdrant_client import QdrantClient

from backend.app.core.config import get_settings
from backend.app.evaluation.golden_dataset import GoldenExample, load_golden_set
from backend.app.evaluation.retriever_eval import retrieve_chunk_ids
from backend.app.ingestion.chunking import Chunk, chunk_document
from backend.app.ingestion.loaders.pdf_loader import extract_pdf
from backend.app.ingestion.pipeline import index_chunk_in_qdrant
from backend.app.models.db_models import DocumentMetadata
from backend.app.models.enums import DocumentSourceType, DocumentStatus

DEFAULT_SOURCE_PDF = "data/raw/pdfs/fr/Loi-de-Finances-complementaire-2015.pdf"
DEFAULT_TOP_K = 5
DEFAULT_EXPERIMENT_NAME = "fiscalmind-chunking-sweep"


@contextmanager
def _temporary_qdrant_collection(collection_name: str):
	"""Point settings.qdrant_collection_loi at a scratch collection for the duration of the
	block, so the existing index_chunk_in_qdrant()/retrieve_chunk_ids() reuse the production
	indexing and hybrid-search code unmodified instead of duplicating it just for this sweep.
	get_settings() is a process-wide singleton, so this is only safe for a single-threaded,
	synchronous script — exactly how this sweep runs."""
	settings = get_settings()
	original_collection = settings.qdrant_collection_loi
	settings.qdrant_collection_loi = collection_name
	try:
		yield
	finally:
		settings.qdrant_collection_loi = original_collection
		client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
		if client.collection_exists(collection_name):
			client.delete_collection(collection_name)


def _resolve_ground_truth(chunks: list[Chunk], golden_set: list[GoldenExample]) -> dict[str, list[str]]:
	"""Re-resolve each golden question's ground truth against *this* chunking variant's actual
	chunk boundaries, by locating which chunk(s) contain its anchor_text — see the anchor_text
	docstring in golden_dataset.py for why chunk_id alone cannot be reused across variants."""
	return {
		example.question: [chunk.chunk_id for chunk in chunks if example.anchor_text in chunk.text]
		for example in golden_set
	}


def _build_scratch_document(source_file: str) -> DocumentMetadata:
	"""An in-memory-only DocumentMetadata, never added to a DB session: index_chunk_in_qdrant()
	only reads its attributes, so no database round-trip is needed for a throwaway sweep run."""
	return DocumentMetadata(
		id=str(uuid.uuid4()),
		source_type=DocumentSourceType.loi,
		titre=source_file,
		langue="fr",
		statut=DocumentStatus.en_vigueur,
		categorie_infraction=["non_classe"],
		storage_path=source_file,
		original_filename=source_file,
		size_bytes=0,
	)


def _build_sweep_eval_dataframe(
	golden_set: list[GoldenExample],
	ground_truth_by_question: dict[str, list[str]],
	top_k: int,
) -> tuple[pd.DataFrame, list[str]]:
	questions, languages, ground_truth, retrieved_context = [], [], [], []
	unresolved: list[str] = []

	for example in golden_set:
		expected_ids = ground_truth_by_question[example.question]
		if not expected_ids:
			unresolved.append(example.question)
			continue
		questions.append(example.question)
		languages.append(example.language)
		ground_truth.append(expected_ids)
		retrieved_context.append(retrieve_chunk_ids(example.question, example.language, top_k))

	eval_df = pd.DataFrame(
		{
			"questions": questions,
			"language": languages,
			"ground_truth": ground_truth,
			"retrieved_context": retrieved_context,
		}
	)
	return eval_df, unresolved


@dataclass
class ChunkingSweepRunResult:
	max_chars: int
	overlap_chars: int
	chunk_count: int
	metrics: dict[str, float]
	run_id: str
	unresolved_questions: list[str]


def _run_single_combo(
	*,
	source_file: str,
	extracted_text: str,
	golden_set: list[GoldenExample],
	max_chars: int,
	overlap_chars: int,
	top_k: int,
) -> ChunkingSweepRunResult:
	chunks = chunk_document(source_file, extracted_text, max_chars=max_chars, overlap_chars=overlap_chars)
	ground_truth_by_question = _resolve_ground_truth(chunks, golden_set)

	collection_name = f"loi_finance_sweep_{uuid.uuid4().hex[:8]}"
	document = _build_scratch_document(source_file)

	with _temporary_qdrant_collection(collection_name):
		for chunk in chunks:
			# Index under chunk.chunk_id itself (not the "{document.id}::{index}" scheme the real
			# /documents upload endpoint uses) so the id_chunk payload Qdrant returns matches
			# exactly what _resolve_ground_truth() computed above from these same Chunk objects.
			index_chunk_in_qdrant(
				chunk.chunk_id,
				document,
				chunk.text,
				numero_article=chunk.numero_article,
			)

		eval_df, unresolved = _build_sweep_eval_dataframe(golden_set, ground_truth_by_question, top_k)

		with mlflow.start_run(run_name=f"max_chars={max_chars}_overlap={overlap_chars}") as run:
			mlflow.log_param("max_chars", max_chars)
			mlflow.log_param("overlap_chars", overlap_chars)
			mlflow.log_param("chunk_count", len(chunks))
			mlflow.log_param("unresolved_questions", len(unresolved))

			results = mlflow.evaluate(
				data=eval_df,
				targets="ground_truth",
				predictions="retrieved_context",
				model_type="retriever",
				evaluators="default",
				extra_metrics=[
					mlflow.metrics.precision_at_k(top_k),
					mlflow.metrics.recall_at_k(top_k),
					mlflow.metrics.ndcg_at_k(top_k),
				],
			)

			return ChunkingSweepRunResult(
				max_chars=max_chars,
				overlap_chars=overlap_chars,
				chunk_count=len(chunks),
				metrics=results.metrics,
				run_id=run.info.run_id,
				unresolved_questions=unresolved,
			)


def run_chunking_sweep(
	*,
	max_chars_options: list[int],
	overlap_chars_options: list[int],
	source_pdf: str = DEFAULT_SOURCE_PDF,
	golden_set: list[GoldenExample] | None = None,
	top_k: int = DEFAULT_TOP_K,
	experiment_name: str = DEFAULT_EXPERIMENT_NAME,
	tracking_uri: str | None = None,
) -> list[ChunkingSweepRunResult]:
	settings = get_settings()
	mlflow.set_tracking_uri(tracking_uri or settings.mlflow_tracking_uri)
	mlflow.set_experiment(experiment_name)

	examples = golden_set if golden_set is not None else load_golden_set()
	extraction = extract_pdf(source_pdf)

	return [
		_run_single_combo(
			source_file=extraction.source_file,
			extracted_text=extraction.text,
			golden_set=examples,
			max_chars=max_chars,
			overlap_chars=overlap_chars,
			top_k=top_k,
		)
		for max_chars in max_chars_options
		for overlap_chars in overlap_chars_options
	]
