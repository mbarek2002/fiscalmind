"""Etape 2 du pilote d'enrichissement LLM : fige l'echantillon de documents.

Composition (reproductible, graine fixe) :
- golden_v1  : documents sources du golden set retrieval_by_article_v1 ;
- golden_v2  : toutes les editions des codes et notes utilisees par en_vigueur_v2
               (reponses attendues, equivalents et pieges) ;
- penalites  : notes communes sur les penalites deja remontees a tort en test ;
- bruit      : petits documents tires au hasard, sans lien avec les questions,
               pour garder une recherche realiste.

Usage (depuis la racine du projet) :
	python -m backend.scripts.pilote_select_documents
"""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

from qdrant_client import QdrantClient

from backend.app.core.config import get_settings

EVAL_DIR = Path(__file__).resolve().parents[1] / "app" / "evaluation"
GOLDEN_V1 = EVAL_DIR / "golden_sets" / "retrieval_by_article_v1.json"
GOLDEN_V2 = EVAL_DIR / "golden_sets" / "en_vigueur_v2.json"
OUTPUT = EVAL_DIR / "pilote" / "documents.json"

PENALITES = ["Note-commune-n-31-4.pdf", "Note-commune-n-37-3.pdf"]
NB_BRUIT = 6
MAX_CHUNKS_BRUIT = 15
GRAINE = 42


def chunk_counts() -> Counter:
	settings = get_settings()
	client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
	counts: Counter = Counter()
	offset = None
	while True:
		points, offset = client.scroll(
			collection_name=settings.qdrant_collection_loi_by_article,
			limit=2000,
			offset=offset,
			with_payload=["source_file"],
			with_vectors=False,
		)
		counts.update(p.payload["source_file"] for p in points)
		if offset is None:
			return counts


def source_of(chunk_id: str) -> str:
	return chunk_id.split("::")[0]


def main() -> None:
	counts = chunk_counts()
	v1 = json.loads(GOLDEN_V1.read_text(encoding="utf-8"))
	v2 = json.loads(GOLDEN_V2.read_text(encoding="utf-8"))["items"]

	groups: dict[str, set[str]] = {
		"golden_v1": {source_of(e["chunk_id"]) for x in v1 for e in x["expected"]},
		"golden_v2": {
			source_of(c)
			for it in v2
			for c in it["attendus"] + it["equivalents"] + [p["chunk"] for p in it["pieges"]]
		},
		"penalites": set(PENALITES),
	}
	chosen = set().union(*groups.values())
	candidates = sorted(
		f for f, n in counts.items()
		if f not in chosen and n <= MAX_CHUNKS_BRUIT and not f.lower().startswith(("code", "loi", "recueil", "cdpf"))
	)
	groups["bruit"] = set(random.Random(GRAINE).sample(candidates, NB_BRUIT))

	missing = sorted(f for g in groups.values() for f in g if f not in counts)
	if missing:
		raise SystemExit(f"Documents absents de Qdrant : {missing}")

	documents = []
	for group, files in groups.items():
		for f in sorted(files):
			if not any(d["fichier"] == f for d in documents):
				documents.append({"fichier": f, "groupe": group, "chunks": counts[f]})

	OUTPUT.parent.mkdir(parents=True, exist_ok=True)
	OUTPUT.write_text(
		json.dumps(
			{"graine": GRAINE, "nb_documents": len(documents), "nb_chunks": sum(d["chunks"] for d in documents), "documents": documents},
			ensure_ascii=False,
			indent=2,
		),
		encoding="utf-8",
	)
	for group in groups:
		docs = [d for d in documents if d["groupe"] == group]
		print(f"{group:10} {len(docs):3} documents  {sum(d['chunks'] for d in docs):5} chunks")
	print(f"{'TOTAL':10} {len(documents):3} documents  {sum(d['chunks'] for d in documents):5} chunks -> {OUTPUT}")


if __name__ == "__main__":
	main()
