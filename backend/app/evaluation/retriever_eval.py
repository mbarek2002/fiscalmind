from __future__ import annotations

from dataclasses import dataclass

import mlflow
import pandas as pd

from backend.app.agents.legal_retrieval import retrieve_legal_candidates
from backend.app.core.config import get_settings
from backend.app.evaluation.golden_dataset import GoldenExample, load_golden_set

DEFAULT_TOP_K = 5
DEFAULT_EXPERIMENT_NAME = "fiscalmind-retrieval-eval"


def retrieve_chunk_ids(question: str, language: str, top_k: int) -> list[str]:
	"""Run the real hybrid retriever and return just the retrieved chunk ids. Shared with
	chunking_sweep.py, which points the same retriever at a scratch Qdrant collection to score
	re-chunked variants."""
	candidates = retrieve_legal_candidates(question=question, language=language, top_k=top_k)
	return [candidate.article_id for candidate in candidates]


def _build_eval_dataframe(golden_set: list[GoldenExample], top_k: int) -> pd.DataFrame:
	"""Precompute retrieval for every golden question into a static dataframe (questions,
	ground_truth, retrieved_context) rather than letting mlflow.evaluate() call the retriever
	itself: this keeps the retrieval call under our own control (easy to debug/mock) and avoids
	depending on mlflow's model-wrapper calling convention for model_type="retriever"."""
	questions: list[str] = []
	languages: list[str] = []
	ground_truth: list[list[str]] = []
	retrieved_context: list[list[str]] = []

	for example in golden_set:
		questions.append(example.question)
		languages.append(example.language)
		ground_truth.append(example.expected_chunk_ids)
		retrieved_context.append(retrieve_chunk_ids(example.question, example.language, top_k))

	return pd.DataFrame(
		{
			"questions": questions,
			"language": languages,
			"ground_truth": ground_truth,
			"retrieved_context": retrieved_context,
		}
	)


@dataclass
class RetrieverEvalResult:
	metrics: dict[str, float]
	run_id: str
	eval_dataframe: pd.DataFrame


def run_retriever_evaluation(
	*,
	golden_set: list[GoldenExample] | None = None,
	top_k: int = DEFAULT_TOP_K,
	experiment_name: str = DEFAULT_EXPERIMENT_NAME,
	tracking_uri: str | None = None,
) -> RetrieverEvalResult:
	settings = get_settings()
	mlflow.set_tracking_uri(tracking_uri or settings.mlflow_tracking_uri)
	mlflow.set_experiment(experiment_name)

	examples = golden_set if golden_set is not None else load_golden_set()
	eval_df = _build_eval_dataframe(examples, top_k)

	with mlflow.start_run() as run:
		mlflow.log_param("top_k", top_k)
		mlflow.log_param("golden_set_size", len(examples))

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

		return RetrieverEvalResult(metrics=results.metrics, run_id=run.info.run_id, eval_dataframe=eval_df)
