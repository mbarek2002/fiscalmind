"""Etape 5 du pilote : construit pilote_base et pilote_ctx sur les 35 documents.

Usage (depuis la racine du projet) :
	python -m backend.scripts.pilote_build_collections
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from backend.app.enrichment.pilot_index import BASE, CTX, build_collections, client

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "backend" / "app" / "evaluation" / "pilote" / "documents.json"
ENRICHED = ROOT / "data" / "eval" / "pilote" / "chunks_enrichis.jsonl"


def load_enrichments() -> dict[str, dict]:
	"""Derniere ligne reussie par chunk (le fichier contient aussi les essais en echec)."""
	rows: dict[str, dict] = {}
	for line in ENRICHED.read_text(encoding="utf-8").splitlines():
		if not line.strip():
			continue
		r = json.loads(line)
		if r["llm_ok"] or r["chunk_id"] not in rows:
			rows[r["chunk_id"]] = r
	return rows


def main() -> None:
	documents = json.loads(SAMPLE.read_text(encoding="utf-8"))["documents"]
	files = [d["fichier"] for d in documents]
	expected = sum(d["chunks"] for d in documents)
	enrichments = load_enrichments()
	print(f"{len(files)} documents, {expected} chunks attendus, {len(enrichments)} enrichissements charges")

	start = time.time()
	counts = build_collections(files, enrichments)
	print(f"construit en {time.time() - start:.0f}s : {counts}")

	c = client()
	for name in (BASE, CTX):
		n = c.count(collection_name=name, exact=True).count
		print(f"{name}: {n} points {'OK' if n == expected else 'ECART !'}")
	missing = sum(1 for p in c.scroll(collection_name=CTX, limit=5000, with_payload=["contexte"])[0] if not p.payload.get("contexte"))
	print(f"chunks sans contexte dans {CTX} : {missing}")


if __name__ == "__main__":
	main()
