import argparse
import json

from backend.app.evaluation.retriever_eval_by_article import (
	DEFAULT_EXPERIMENT_NAME,
	DEFAULT_TOP_K,
	run_retriever_evaluation_by_article,
)


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Evaluate the by-article retriever (E5 + BM25 natif) against its golden set via MLflow"
	)
	parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
	parser.add_argument("--experiment-name", default=DEFAULT_EXPERIMENT_NAME)
	parser.add_argument("--tracking-uri", default=None)
	args = parser.parse_args()

	result = run_retriever_evaluation_by_article(
		top_k=args.top_k,
		experiment_name=args.experiment_name,
		tracking_uri=args.tracking_uri,
	)

	print(json.dumps(result.metrics, indent=2))
	print(f"MLflow run: {result.run_id} (experiment: {args.experiment_name})")


if __name__ == "__main__":
	main()
