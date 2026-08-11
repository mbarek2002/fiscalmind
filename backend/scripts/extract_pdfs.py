import argparse
import json
from dataclasses import asdict
from pathlib import Path

from backend.app.ingestion.chunking import chunk_document
from backend.app.ingestion.loaders.pdf_loader import PDFExtractionError, extract_pdf, iter_pdf_paths


def main() -> None:
	parser = argparse.ArgumentParser(description="Extract text from PDFs and split into chunks")
	parser.add_argument("--source", required=True, help="Directory containing source PDFs (searched recursively)")
	parser.add_argument("--output", required=True, help="Directory to write chunks.jsonl and extraction_report.json")
	parser.add_argument("--limit", type=int, default=None, help="Only process the first N PDFs (for sampling)")
	args = parser.parse_args()

	output_dir = Path(args.output)
	output_dir.mkdir(parents=True, exist_ok=True)

	pdf_paths = iter_pdf_paths(args.source)
	if args.limit:
		pdf_paths = pdf_paths[: args.limit]

	report = {"total_files": len(pdf_paths), "succeeded": 0, "failed": 0, "total_chunks": 0, "errors": [], "warnings": []}

	chunks_path = output_dir / "chunks.jsonl"
	with chunks_path.open("w", encoding="utf-8") as chunks_file:
		for pdf_path in pdf_paths:
			try:
				extraction = extract_pdf(pdf_path)
			except PDFExtractionError as exc:
				report["failed"] += 1
				report["errors"].append(f"{pdf_path.name}: {exc}")
				continue

			if extraction.warnings:
				report["warnings"].extend(f"{pdf_path.name}: {warning}" for warning in extraction.warnings)

			chunks = chunk_document(extraction.source_file, extraction.text)
			for chunk in chunks:
				chunks_file.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

			report["succeeded"] += 1
			report["total_chunks"] += len(chunks)

	report_path = output_dir / "extraction_report.json"
	report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
	print(json.dumps({k: v for k, v in report.items() if k not in {"errors", "warnings"}}, indent=2))
	print(f"Report written to {report_path}")
	print(f"Chunks written to {chunks_path}")


if __name__ == "__main__":
	main()
