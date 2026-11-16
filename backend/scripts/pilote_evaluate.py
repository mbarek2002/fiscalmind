"""Etape 6 du pilote : evalue les 4 variantes sur les golden sets v1 et v2.

Pour chaque question et chaque variante : recherche top 5, generation de la
reponse (NVIDIA), jugement (LLM juge). Resultats : console, MLflow (experience
fiscalmind-pilote-enrichissement, un run par variante) et
data/eval/pilote/resultats_etape6.json.

Usage (depuis la racine du projet) :
	python -m backend.scripts.pilote_evaluate [--workers 8] [--limit N] [--sans-generation]
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import mlflow

from backend.app.core.config import get_settings
from backend.app.enrichment.pilot_index import search
from backend.app.evaluation.golden_dataset_by_article import load_golden_set
from backend.app.evaluation.llm_judge import CORRECTNESS_PROMPT, REFUSAL_PROMPT, JudgeClient
from backend.app.evaluation.pilot_eval import (
	JUDGE_V2_PROMPT, SYSTEM_PROMPT, VARIANTS, generation_prompt, mean, ndcg_at_k, recall_at_k, reciprocal_rank,
	vigueur_metrics,
)
from backend.app.ingestion.indexing_by_article import fetch_chunk_texts
from backend.app.llm.factory import get_llm_client

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_V2 = ROOT / "backend" / "app" / "evaluation" / "golden_sets" / "en_vigueur_v2.json"
OUTPUT = ROOT / "data" / "eval" / "pilote" / "resultats_etape6.json"
EXPERIMENT = "fiscalmind-pilote-enrichissement"


def load_questions() -> list[dict]:
	questions = []
	for ex in load_golden_set():
		questions.append({
			"set": "v1", "question": ex.question, "expected": [e.chunk_id for e in ex.expected],
			"unanswerable": ex.is_unanswerable,
		})
	for it in json.loads(GOLDEN_V2.read_text(encoding="utf-8"))["items"]:
		questions.append({
			"set": "v2", "id": it["id"], "question": it["question"], "correct": it["attendus"] + it["equivalents"],
			"traps": [p["chunk"] for p in it["pieges"]], "reference": it["reponse_attendue"],
			"faits_cles": it["faits_cles"], "faits_errones": it["faits_errones"],
		})
	return questions


def main() -> None:
	parser = argparse.ArgumentParser()
	parser.add_argument("--workers", type=int, default=8)
	parser.add_argument("--limit", type=int, default=None)
	parser.add_argument("--sans-generation", action="store_true", help="metriques de recherche seulement")
	args = parser.parse_args()

	questions = load_questions()
	if args.limit:
		questions = questions[: args.limit]
	references = fetch_chunk_texts(sorted({c for q in questions if q["set"] == "v1" for c in q["expected"]}))
	generator = get_llm_client()
	judge = JudgeClient()
	print(f"{len(questions)} questions x {len(VARIANTS)} variantes | generateur {get_settings().llm_provider} | juge {judge.model}", flush=True)

	def run(task: tuple[str, dict]) -> dict:
		variant, q = task
		collection, statut = VARIANTS[variant]
		hits = search(collection, q["question"], top_k=5, prefer_en_vigueur=statut)
		ids = [h.id_chunk for h in hits]
		row = {"variant": variant, **{k: q[k] for k in ("set", "question")}, "retrieved": ids}
		if q["set"] == "v1" and not q["unanswerable"]:
			row.update(recall5=recall_at_k(ids, q["expected"]), ndcg5=ndcg_at_k(ids, q["expected"]), rr=reciprocal_rank(ids, q["expected"]))
		if q["set"] == "v2":
			row["id"] = q["id"]
			row.update(vigueur_metrics(ids, q["correct"], q["traps"]).__dict__)
		if args.sans_generation:
			return row
		try:
			answer = generator.generate(prompt=generation_prompt(q["question"], hits, statut), system_prompt=SYSTEM_PROMPT)
			row["answer"] = answer
			if q["set"] == "v2":
				verdict = judge.ask_json(JUDGE_V2_PROMPT.format(
					question=q["question"], reference=q["reference"], faits_cles="; ".join(q["faits_cles"]),
					faits_errones="; ".join(q["faits_errones"]) or "aucune", answer=answer))
				row.update(score=int(verdict["score"]), verdict=verdict.get("verdict"), regle_perimee=bool(verdict.get("regle_perimee")))
			elif q["unanswerable"]:
				verdict = judge.ask_json(REFUSAL_PROMPT.format(question=q["question"], answer=answer))
				row["refused"] = bool(verdict.get("refused"))
			else:
				reference = "\n\n---\n\n".join(references.get(c, "") for c in q["expected"])
				verdict = judge.ask_json(CORRECTNESS_PROMPT.format(question=q["question"], reference=reference, answer=answer))
				row.update(score=int(verdict["score"]), verdict=verdict.get("verdict"))
			row["justification"] = verdict.get("justification", "")
		except Exception as exc:
			row["error"] = repr(exc)
		return row

	tasks = [(v, q) for v in VARIANTS for q in questions]
	start = time.time()
	with ThreadPoolExecutor(args.workers) as pool:
		rows = list(pool.map(run, tasks))
	print(f"{len(rows)} evaluations en {time.time() - start:.0f}s", flush=True)

	summary = {}
	for variant in VARIANTS:
		r = [x for x in rows if x["variant"] == variant]
		v1 = [x for x in r if x["set"] == "v1" and "recall5" in x]
		v2 = [x for x in r if x["set"] == "v2"]
		unans = [x for x in r if x["set"] == "v1" and "refused" in x]
		summary[variant] = {
			"v1_recall5": mean([x["recall5"] for x in v1]),
			"v1_ndcg5": mean([x["ndcg5"] for x in v1]),
			"v1_mrr": mean([x["rr"] for x in v1]),
			"v1_judge_score": mean([x.get("score") for x in v1]),
			"v1_refusal_rate": mean([float(x["refused"]) for x in unans]),
			"v2_correct_in_top5": mean([float(x["correct_in_top5"]) for x in v2]),
			"v2_correct_before_trap": mean([float(x["correct_before_trap"]) for x in v2]),
			"v2_trap_at_1": mean([float(x["trap_at_1"]) for x in v2]),
			"v2_trap_share_top5": mean([x["trap_share_top5"] for x in v2]),
			"v2_judge_score": mean([x.get("score") for x in v2]),
			"v2_correct_rate": mean([float(x.get("verdict") == "correct") for x in v2 if "verdict" in x]),
			"v2_regle_perimee_rate": mean([float(x["regle_perimee"]) for x in v2 if "regle_perimee" in x]),
			"errors": float(sum("error" in x for x in r)),
		}

	OUTPUT.parent.mkdir(parents=True, exist_ok=True)
	OUTPUT.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

	settings = get_settings()
	mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
	mlflow.set_experiment(EXPERIMENT)
	for variant, metrics in summary.items():
		with mlflow.start_run(run_name=variant):
			collection, statut = VARIANTS[variant]
			mlflow.log_params({"collection": collection, "prefer_en_vigueur": statut, "questions": len(questions), "judge_model": judge.model})
			for name, value in metrics.items():
				if value is not None:
					mlflow.log_metric(name, float(value))
			mlflow.log_artifact(str(OUTPUT))

	names = list(next(iter(summary.values())).keys())
	print("\n" + f"{'metrique':26}" + "".join(f"{v:>16}" for v in VARIANTS))
	for name in names:
		cells = "".join(f"{(summary[v][name] if summary[v][name] is not None else float('nan')):>16.3f}" for v in VARIANTS)
		print(f"{name:26}{cells}")
	print(f"\nRapport : {OUTPUT}")


if __name__ == "__main__":
	main()
