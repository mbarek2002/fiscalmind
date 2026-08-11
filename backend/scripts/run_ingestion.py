import argparse
import json

from backend.app.ingestion.pipeline import ingest_source_directory_sync


def main() -> None:
	parser = argparse.ArgumentParser(description="Run FiscalMind document ingestion")
	parser.add_argument("--source", required=True, help="Path to source directory containing .txt/.md documents")
	parser.add_argument(
		"--source-type",
		default="loi",
		choices=["loi", "jurisprudence"],
		help="Document source type",
	)
	args = parser.parse_args()

	result = ingest_source_directory_sync(source_dir=args.source, source_type=args.source_type)
	print(json.dumps(result.__dict__, ensure_ascii=True, indent=2))


if __name__ == "__main__":
	main()
