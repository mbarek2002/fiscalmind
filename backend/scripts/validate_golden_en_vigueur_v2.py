"""Verifie le golden set 'en vigueur' v2 contre la collection Qdrant.

Pour chaque question :
- chaque chunk attendu / equivalent existe ;
- chaque preuve (citation exacte) se trouve dans au moins un chunk attendu ;
- chaque piege existe et contient bien son marqueur (l'ancienne valeur).

Usage (depuis la racine du projet) :
	python -m backend.scripts.validate_golden_en_vigueur_v2
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from backend.app.ingestion.indexing_by_article import fetch_chunk_texts

GOLDEN_PATH = Path(__file__).resolve().parents[1] / "app" / "evaluation" / "golden_sets" / "en_vigueur_v2.json"


def normalize(text: str) -> str:
	"""Espaces multiples, retours a la ligne et apostrophes typographiques unifies."""
	return re.sub(r"\s+", " ", text.replace("’", "'")).strip()


def validate(items: list[dict]) -> list[str]:
	ids = {c for it in items for c in it["attendus"] + it["equivalents"] + [p["chunk"] for p in it["pieges"]]}
	texts = {k: normalize(v) for k, v in fetch_chunk_texts(sorted(ids)).items()}
	errors: list[str] = []

	for it in items:
		qid = it["id"]
		for chunk in it["attendus"] + it["equivalents"]:
			if chunk not in texts:
				errors.append(f"{qid}: chunk absent de Qdrant : {chunk}")
		expected_text = " ".join(texts.get(c, "") for c in it["attendus"])
		for proof in it["preuves"]:
			if normalize(proof) not in expected_text:
				errors.append(f"{qid}: preuve introuvable dans les chunks attendus : {proof!r}")
		for trap in it["pieges"]:
			if trap["chunk"] not in texts:
				errors.append(f"{qid}: piege absent de Qdrant : {trap['chunk']}")
			elif normalize(trap["marqueur"]) not in texts[trap["chunk"]]:
				errors.append(f"{qid}: marqueur {trap['marqueur']!r} absent du piege {trap['chunk']}")
	return errors


def main() -> None:
	data = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
	items = data["items"]
	errors = validate(items)
	n_traps = sum(len(it["pieges"]) for it in items)
	print(f"{len(items)} questions, {n_traps} pieges verifies contre Qdrant")
	if errors:
		print(f"\n{len(errors)} erreur(s) :")
		for e in errors:
			print(f"  - {e}")
		sys.exit(1)
	print("OK : toutes les preuves et tous les pieges sont retrouves dans les textes indexes.")


if __name__ == "__main__":
	main()
