from __future__ import annotations

from backend.app.enrichment.pilot_index import PilotHit
from backend.app.evaluation.pilot_eval import generation_prompt, ndcg_at_k, recall_at_k, reciprocal_rank, vigueur_metrics


def test_retrieval_metrics() -> None:
	retrieved = ["a", "x", "b", "y", "z"]
	assert recall_at_k(retrieved, ["a", "b"]) == 1.0
	assert recall_at_k(retrieved, ["a", "c"]) == 0.5
	assert reciprocal_rank(retrieved, ["b"]) == 1 / 3
	assert ndcg_at_k(["a", "b"], ["a", "b"]) == 1.0
	assert 0 < ndcg_at_k(["x", "a"], ["a"]) < 1


def test_vigueur_metrics_correct_before_trap() -> None:
	m = vigueur_metrics(["cdpf2025", "cdpf2018", "x"], correct=["cdpf2025"], traps=["cdpf2018"])
	assert m.correct_in_top5 and m.correct_before_trap and not m.trap_at_1
	assert abs(m.trap_share_top5 - 1 / 3) < 1e-9


def test_vigueur_metrics_trap_first() -> None:
	m = vigueur_metrics(["note2019", "cdpf2025"], correct=["cdpf2025"], traps=["note2019"])
	assert m.correct_in_top5 and not m.correct_before_trap and m.trap_at_1


def test_vigueur_metrics_no_correct_source() -> None:
	m = vigueur_metrics(["x", "y"], correct=["cdpf2025"], traps=[])
	assert not m.correct_in_top5 and not m.correct_before_trap


def test_generation_prompt_shows_statut_only_when_asked() -> None:
	hit = PilotHit(id_chunk="c", source_file="cdpf-2025.pdf", texte="Article 81 ...", score=1.0, statut_version="en_vigueur", annee=2025, payload={})
	with_statut = generation_prompt("Q ?", [hit], with_statut=True)
	without = generation_prompt("Q ?", [hit], with_statut=False)
	assert "edition en vigueur" in with_statut and "EN VIGUEUR" in with_statut
	assert "edition en vigueur" not in without
