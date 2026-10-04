import argparse
import json

from backend.app.evaluation.chunking_sweep import (
	DEFAULT_EXPERIMENT_NAME,
	DEFAULT_SOURCE_PDF,
	DEFAULT_TOP_K,
	run_chunking_sweep,
)


def _parse_int_list(value: str) -> list[int]:
	return [int(item) for item in value.split(",") if item.strip()]


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Sweep chunk_document() parameters and track retrieval metrics per combination in MLflow"
	)
	parser.add_argument("--max-chars", type=_parse_int_list, default=[600, 1200, 1800], help="Comma-separated max_chars values")
	parser.add_argument("--overlap-chars", type=_parse_int_list, default=[150], help="Comma-separated overlap_chars values")
	parser.add_argument("--source-pdf", default=DEFAULT_SOURCE_PDF)
	parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
	parser.add_argument("--experiment-name", default=DEFAULT_EXPERIMENT_NAME)
	args = parser.parse_args()

	results = run_chunking_sweep(
		max_chars_options=args.max_chars,
		overlap_chars_options=args.overlap_chars,
		source_pdf=args.source_pdf,
		top_k=args.top_k,
		experiment_name=args.experiment_name,
	)

	for result in results:
		print(
			json.dumps(
				{
					"max_chars": result.max_chars,
					"overlap_chars": result.overlap_chars,
					"chunk_count": result.chunk_count,
					"run_id": result.run_id,
					"unresolved_questions": result.unresolved_questions,
					**result.metrics,
				},
				indent=2,
			)
		)


if __name__ == "__main__":
	main()
