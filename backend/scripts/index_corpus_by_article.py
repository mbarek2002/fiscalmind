import argparse
import time
from pathlib import Path

from backend.app.ingestion.chunking_by_article import chunk_by_article, extract_pdf_pages
from backend.app.ingestion.indexing_by_article import index_chunks_by_article

DEFAULT_SOURCE_DIR = Path("data/raw/pdfs/fr")


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Indexe tout (ou une partie) du corpus PDF dans loi_finance_by_article (pipeline E5 + chunking par article + BM25 natif)"
	)
	parser.add_argument("--source", default=str(DEFAULT_SOURCE_DIR), help="Dossier contenant les PDF a indexer")
	parser.add_argument("--limit", type=int, default=None, help="Limiter aux N premiers fichiers (tri alphabetique), pour un test rapide")
	args = parser.parse_args()

	source_dir = Path(args.source)
	pdf_paths = sorted(source_dir.glob("*.pdf"))
	if args.limit:
		pdf_paths = pdf_paths[: args.limit]

	total = len(pdf_paths)
	print(f"{total} fichiers a indexer depuis {source_dir}")

	succeeded = 0
	failed: list[str] = []
	total_chunks = 0
	total_with_article = 0
	total_fallback = 0
	start = time.time()

	for i, pdf_path in enumerate(pdf_paths, start=1):
		try:
			pages = extract_pdf_pages(pdf_path)
			chunks = chunk_by_article(pdf_path.name, pages)
			index_chunks_by_article(chunks)

			total_chunks += len(chunks)
			total_with_article += sum(1 for c in chunks if c.numero_article is not None)
			if any(c.headers.get("chunking_fallback") for c in chunks):
				total_fallback += len(chunks)
			succeeded += 1
		except Exception as exc:
			failed.append(f"{pdf_path.name}: {exc!r}")

		if i % 20 == 0 or i == total:
			elapsed = time.time() - start
			print(f"[{i}/{total}] {succeeded} OK, {len(failed)} echecs, {total_chunks} chunks indexes ({elapsed:.0f}s ecoulees)")

	elapsed = time.time() - start
	print()
	print(f"Termine en {elapsed:.0f}s ({elapsed/60:.1f} min)")
	print(f"Fichiers traites : {succeeded}/{total}")
	print(f"Chunks indexes au total : {total_chunks}")
	print(f"  dont avec numero_article : {total_with_article}")
	print(f"  dont issus du fallback taille : {total_fallback}")

	if failed:
		print(f"\n{len(failed)} echecs :")
		for line in failed:
			print(f"  - {line}")


if __name__ == "__main__":
	main()
