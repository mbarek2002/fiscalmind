"""Etape 4 du pilote : enrichissement de chaque chunk de l'echantillon.

Entree : la fiche de chaque document (data/eval/pilote/fiches_documents.json).
Sortie : data/eval/pilote/chunks_enrichis.jsonl (une ligne par chunk), ecrite au
fil de l'eau ; un relancement reprend la ou il s'est arrete.

Usage (depuis la racine du projet) :
	python -m backend.scripts.pilote_passe2_chunks [--workers 16] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from backend.app.enrichment.chunk_context import build_prompt, enrich_chunk
from backend.app.enrichment.document_fiche import FicheLLM
from backend.app.ingestion.indexing_by_article import fetch_document_chunks

ROOT = Path(__file__).resolve().parents[2]
FICHES = ROOT / "data" / "eval" / "pilote" / "fiches_documents.json"
OUTPUT = ROOT / "data" / "eval" / "pilote" / "chunks_enrichis.jsonl"


def load_done() -> set[str]:
	if not OUTPUT.exists():
		return set()
	done = set()
	for line in OUTPUT.read_text(encoding="utf-8").splitlines():
		if line.strip():
			row = json.loads(line)
			if row.get("llm_ok"):
				done.add(row["chunk_id"])
	return done


def main() -> None:
	parser = argparse.ArgumentParser()
	parser.add_argument("--workers", type=int, default=16)
	parser.add_argument("--limit", type=int, default=None, help="N premiers chunks a traiter (test)")
	args = parser.parse_args()

	fiches = {f["fichier"]: f for f in json.loads(FICHES.read_text(encoding="utf-8"))["fiches"]}
	tasks = []
	for fichier, fiche in fiches.items():
		chunks = fetch_document_chunks(fichier)
		for i, (chunk_id, text) in enumerate(chunks):
			before = chunks[i - 1][1] if i > 0 else ""
			after = chunks[i + 1][1] if i + 1 < len(chunks) else ""
			tasks.append((chunk_id, text, fiche, before, after))

	done = load_done()
	todo = [t for t in tasks if t[0] not in done]
	if args.limit:
		todo = todo[: args.limit]
	print(f"{len(tasks)} chunks, {len(done)} deja faits, {len(todo)} a traiter", flush=True)

	llm = FicheLLM()
	lock = threading.Lock()
	stats: Counter = Counter()

	def process(task: tuple) -> dict:
		chunk_id, text, fiche, before, after = task
		try:
			# 1500 : les chunks de baremes (dizaines de montants) depassaient 800 tokens
			# et le JSON tronque etait inexploitable.
			raw = llm.ask_json(build_prompt(fiche, text, before, after), max_tokens=1500)
		except Exception:
			raw = None
		return enrich_chunk(chunk_id, text, fiche, raw).to_dict()

	start = time.time()
	OUTPUT.parent.mkdir(parents=True, exist_ok=True)
	with OUTPUT.open("a", encoding="utf-8") as out, ThreadPoolExecutor(args.workers) as pool:
		futures = [pool.submit(process, t) for t in todo]
		for i, future in enumerate(as_completed(futures), start=1):
			row = future.result()
			with lock:
				out.write(json.dumps(row, ensure_ascii=False) + "\n")
				out.flush()
				stats["ok" if row["llm_ok"] else "echec"] += 1
				stats[f"contexte_{row['contexte_source']}"] += 1
				stats["rejets"] += len(row["rejets"])
			if i % 100 == 0 or i == len(todo):
				elapsed = time.time() - start
				print(f"[{i}/{len(todo)}] {elapsed:5.0f}s  {i / elapsed * 60:4.0f} chunks/min  {dict(stats)}", flush=True)

	print(f"\nTermine en {time.time() - start:.0f}s -> {OUTPUT}")


if __name__ == "__main__":
	main()
