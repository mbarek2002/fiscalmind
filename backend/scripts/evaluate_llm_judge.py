"""Evalue l'agent simple (pipeline par article) avec un LLM juge + RAGAS.

Usage (depuis la racine du projet) :
	python -m backend.scripts.evaluate_llm_judge [--limit N] [--no-ragas]

Le generateur est LLM_PROVIDER ; le juge est JUDGE_PROVIDER / JUDGE_MODEL.
Resultats : console + MLflow (experience fiscalmind-llm-judge) + JSON dans data/eval/.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import mlflow

from backend.app.core.config import get_settings
from backend.app.evaluation.golden_dataset_by_article import load_golden_set
from backend.app.evaluation.llm_judge import JudgeClient, run_llm_judge, summary_to_dict

EXPERIMENT = "fiscalmind-llm-judge"
OUTPUT_DIR = Path("data/eval")


def _progress(i: int, total: int, item) -> None:
	if item.error:
		status = f"ERREUR {item.error[:80]}"
	elif item.is_unanswerable:
		status = f"sans reponse -> refus={item.refused}"
	else:
		status = f"note={item.score} ({item.verdict}), article attendu retrouve={item.expected_retrieved}"
	print(f"[{i}/{total}] {item.agent_seconds:5.1f}s  {status}", flush=True)


def _mean(values: list) -> float | None:
	clean = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
	return sum(clean) / len(clean) if clean else None


def main() -> None:
	parser = argparse.ArgumentParser()
	parser.add_argument("--limit", type=int, default=None, help="N premieres questions seulement (test rapide)")
	parser.add_argument("--no-ragas", action="store_true", help="Sauter Faithfulness / AnswerRelevancy")
	args = parser.parse_args()

	settings = get_settings()
	golden = load_golden_set()
	if args.limit:
		golden = golden[: args.limit]

	judge = JudgeClient(settings)
	generator = settings.nvidia_llm_model if settings.llm_provider == "nvidia" else settings.llm_provider
	print(f"Generateur : {settings.llm_provider} / {generator}")
	print(f"Juge       : {settings.judge_provider} / {judge.model}")
	print(f"Questions  : {len(golden)}\n")

	summary, agent_results = run_llm_judge(golden, judge=judge, on_progress=_progress)

	ragas_scores: dict[str, float | None] = {}
	if not args.no_ragas:
		from backend.app.evaluation.ragas_eval import dataset_from_results, evaluate_ragas_dataset

		answerable = [r for r, ex in zip(agent_results, golden) if not ex.is_unanswerable and r.answer]
		if answerable:
			print(f"\nRAGAS sur {len(answerable)} reponses...", flush=True)
			df = evaluate_ragas_dataset(dataset_from_results(answerable)).to_pandas()
			ragas_scores = {
				"faithfulness": _mean(df["faithfulness"].tolist()),
				"answer_relevancy": _mean(df["answer_relevancy"].tolist()),
			}

	metrics = {
		"judge_mean_score": summary.mean_score,
		"judge_correct_rate": summary.correct_rate,
		"judge_partial_rate": summary.partial_rate,
		"judge_incorrect_rate": summary.incorrect_rate,
		"unanswerable_refusal_rate": summary.refusal_rate,
		"retrieval_hit_rate_top5": summary.retrieval_hit_rate,
		"mean_agent_seconds": summary.mean_agent_seconds,
		"n_errors": summary.n_errors,
		**ragas_scores,
	}

	OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
	report_path = OUTPUT_DIR / f"llm_judge_{datetime.now():%Y%m%d_%H%M%S}.json"
	report = {"metrics": metrics, **summary_to_dict(summary)}
	report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

	mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
	mlflow.set_experiment(EXPERIMENT)
	with mlflow.start_run() as run:
		mlflow.log_params(
			{
				"generator_provider": settings.llm_provider,
				"generator_model": generator,
				"judge_provider": settings.judge_provider,
				"judge_model": judge.model,
				"golden_set_size": len(golden),
				"qdrant_collection": settings.qdrant_collection_loi_by_article,
			}
		)
		for name, value in metrics.items():
			if value is not None:
				mlflow.log_metric(name, float(value))
		mlflow.log_artifact(str(report_path))

	print("\n=== RESULTATS ===")
	for name, value in metrics.items():
		print(f"{name:28} {value if value is None else round(float(value), 3)}")
	print(f"\nRapport : {report_path}")
	print(f"MLflow  : {run.info.run_id} (experience {EXPERIMENT})")


if __name__ == "__main__":
	main()
