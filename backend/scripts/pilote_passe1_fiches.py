"""Etape 3 du pilote : une fiche par document (regles + LLM + statut d'edition).

Lit l'echantillon fige (app/evaluation/pilote/documents.json), reconstitue le
texte de chaque document depuis Qdrant, puis ecrit data/eval/pilote/fiches_documents.json.
Reprise automatique : les documents deja traites avec succes sont sautes.

Usage (depuis la racine du projet) :
	python -m backend.scripts.pilote_passe1_fiches [--workers 6] [--refaire]
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from backend.app.enrichment.document_fiche import FicheLLM, merge_fiche
from backend.app.enrichment.document_rules import extract_rule_facts
from backend.app.enrichment.versions import compute_version_status
from backend.app.ingestion.indexing_by_article import fetch_document_chunks, list_source_files

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "backend" / "app" / "evaluation" / "pilote" / "documents.json"
OUTPUT = ROOT / "data" / "eval" / "pilote" / "fiches_documents.json"
PAGE_CHARS = 4000


def load_existing() -> dict[str, dict]:
	if not OUTPUT.exists():
		return {}
	return {f["fichier"]: f for f in json.loads(OUTPUT.read_text(encoding="utf-8"))["fiches"]}


def save(fiches: dict[str, dict]) -> None:
	OUTPUT.parent.mkdir(parents=True, exist_ok=True)
	ordered = sorted(fiches.values(), key=lambda f: (f["famille"], f["fichier"]))
	OUTPUT.write_text(json.dumps({"nb": len(ordered), "fiches": ordered}, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
	parser = argparse.ArgumentParser()
	parser.add_argument("--workers", type=int, default=6)
	parser.add_argument("--refaire", action="store_true", help="ignorer les fiches deja calculees")
	args = parser.parse_args()

	documents = [d["fichier"] for d in json.loads(SAMPLE.read_text(encoding="utf-8"))["documents"]]
	versions = compute_version_status(list_source_files())  # statut calcule sur TOUT le corpus
	fiches = {} if args.refaire else load_existing()
	todo = [f for f in documents if not (f in fiches and fiches[f].get("llm_ok"))]
	print(f"{len(documents)} documents, {len(todo)} a traiter ({len(documents) - len(todo)} deja faits)")

	llm = FicheLLM()

	def process(fichier: str) -> dict:
		chunks = fetch_document_chunks(fichier)
		text = "\n".join(t for _, t in chunks)
		rules = extract_rule_facts(fichier, text[:PAGE_CHARS], text[-PAGE_CHARS:])
		try:
			raw = llm.fiche(fichier, text)
		except Exception as exc:
			print(f"  ! LLM en echec pour {fichier} : {exc}")
			raw = None
		return merge_fiche(fichier, rules, versions[fichier], raw, text, len(chunks)).to_dict()

	start = time.time()
	with ThreadPoolExecutor(args.workers) as pool:
		futures = {pool.submit(process, f): f for f in todo}
		for i, future in enumerate(as_completed(futures), start=1):
			fiche = future.result()
			fiches[fiche["fichier"]] = fiche
			save(fiches)
			flags = []
			if fiche["rejets"]:
				flags.append(f"{len(fiche['rejets'])} rejet(s)")
			if fiche["conflits"]:
				flags.append(f"{len(fiche['conflits'])} conflit(s)")
			print(
				f"[{i}/{len(todo)}] {time.time() - start:5.0f}s  {fiche['famille']:12} {str(fiche['annee']):>4} "
				f"({fiche['annee_source']}) {fiche['statut_version']:11} {fiche['fichier'][:50]}  {' '.join(flags)}",
				flush=True,
			)

	all_fiches = [fiches[f] for f in documents if f in fiches]
	print("\n=== BILAN")
	print(f"fiches : {len(all_fiches)} | LLM ok : {sum(f['llm_ok'] for f in all_fiches)}")
	print(f"annee trouvee : {sum(f['annee'] is not None for f in all_fiches)} "
		f"(regles : {sum(f['annee_source'] in ('nom_fichier', 'premiere_page', 'derniere_page') for f in all_fiches)}, "
		f"llm : {sum(f['annee_source'] == 'llm' for f in all_fiches)})")
	print(f"champs LLM rejetes (preuve absente) : {sum(len(f['rejets']) for f in all_fiches)}")
	print(f"conflits regles/LLM : {sum(len(f['conflits']) for f in all_fiches)}")
	print(f"-> {OUTPUT}")


if __name__ == "__main__":
	main()
