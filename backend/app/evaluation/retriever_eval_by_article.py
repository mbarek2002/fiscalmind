from __future__ import annotations

from dataclasses import dataclass

import mlflow
import pandas as pd

from backend.app.core.config import get_settings
from backend.app.evaluation.golden_dataset_by_article import GoldenExampleByArticle, load_golden_set
from backend.app.ingestion.indexing_by_article import get_top_dense_score, search_by_article_hybrid

DEFAULT_TOP_K = 5
DEFAULT_EXPERIMENT_NAME = "fiscalmind-retrieval-eval-by-article"


def retrieve_chunk_ids(question: str, language: str, top_k: int) -> list[str]:
	results = search_by_article_hybrid(question=question, language=language, top_k=top_k)
	return [r.id_chunk for r in results]


def _build_eval_dataframe(golden_set: list[GoldenExampleByArticle], top_k: int) -> pd.DataFrame:
	"""Seules les questions avec une reponse connue vont dans ce dataframe -- les
	questions is_unanswerable n'ont pas de ground_truth possible (recall/precision
	n'ont pas de sens pour elles), elles sont evaluees a part par
	_evaluate_unanswerable()."""
	questions, languages, ground_truth, retrieved_context = [], [], [], []

	for example in golden_set:
		if example.is_unanswerable or not example.expected:
			continue
		retrieved_ids = retrieve_chunk_ids(example.question, example.language, top_k)
		questions.append(example.question)
		languages.append(example.language)
		ground_truth.append([e.chunk_id for e in example.expected])
		retrieved_context.append(retrieved_ids)

	return pd.DataFrame(
		{
			"questions": questions,
			"language": languages,
			"ground_truth": ground_truth,
			"retrieved_context": retrieved_context,
		}
	)


def _calibrate_no_answer_threshold(golden_set: list[GoldenExampleByArticle]) -> float | None:
	"""Seuil calibre empiriquement a partir du score dense brut des questions AVEC
	reponse connue, plutot qu'une valeur fixe arbitraire -- les similarites E5
	sont naturellement compressees dans une plage haute (caracteristique connue
	du modele), donc un seuil absolu invente a l'avance (ex: 0.5) n'a pas de sens
	sans etre rapporte a la distribution reelle de ce corpus/modele. Le seuil
	retenu est le score le plus bas observe parmi les vraies correspondances :
	toute question sans reponse qui score EN-DESSOUS est un signal plus faible
	que n'importe quelle vraie correspondance connue."""
	answerable = [e for e in golden_set if not e.is_unanswerable and e.expected]
	if not answerable:
		return None
	scores = [get_top_dense_score(e.question, e.language) for e in answerable]
	return min(scores)


def _evaluate_unanswerable(golden_set: list[GoldenExampleByArticle], threshold: float | None) -> dict[str, float]:
	"""Pour chaque question sans reponse connue, verifie si le score dense brut
	(pas le score RRF -- voir get_top_dense_score) reste sous le seuil calibre --
	un score au-dessus serait un signe d'hallucination potentielle (le systeme
	retourne un resultat confiant sur un sujet que le corpus ne couvre pas)."""
	unanswerable = [e for e in golden_set if e.is_unanswerable]
	if not unanswerable or threshold is None:
		return {}

	correct_refusals = sum(1 for e in unanswerable if get_top_dense_score(e.question, e.language) < threshold)

	return {
		"unanswerable_total": float(len(unanswerable)),
		"unanswerable_correct_refusal_rate": correct_refusals / len(unanswerable),
		"unanswerable_calibrated_threshold": threshold,
	}


@dataclass
class RetrieverEvalByArticleResult:
	metrics: dict[str, float]
	run_id: str
	eval_dataframe: pd.DataFrame


def run_retriever_evaluation_by_article(
	*,
	golden_set: list[GoldenExampleByArticle] | None = None,
	top_k: int = DEFAULT_TOP_K,
	experiment_name: str = DEFAULT_EXPERIMENT_NAME,
	tracking_uri: str | None = None,
) -> RetrieverEvalByArticleResult:
	settings = get_settings()
	mlflow.set_tracking_uri(tracking_uri or settings.mlflow_tracking_uri)
	mlflow.set_experiment(experiment_name)

	examples = golden_set if golden_set is not None else load_golden_set()
	eval_df = _build_eval_dataframe(examples, top_k)
	threshold = _calibrate_no_answer_threshold(examples)
	unanswerable_metrics = _evaluate_unanswerable(examples, threshold)

	with mlflow.start_run() as run:
		mlflow.log_param("top_k", top_k)
		mlflow.log_param("golden_set_size", len(examples))
		mlflow.log_param("embedding_model", settings.e5_embedding_model_name)
		mlflow.log_param("qdrant_collection", settings.qdrant_collection_loi_by_article)
		mlflow.log_param("no_answer_threshold_calibration", "min_of_answerable_top_dense_scores")

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

		for name, value in unanswerable_metrics.items():
			mlflow.log_metric(name, value)

		return RetrieverEvalByArticleResult(
			metrics={**results.metrics, **unanswerable_metrics},
			run_id=run.info.run_id,
			eval_dataframe=eval_df,
		)
