from __future__ import annotations

from backend.app.enrichment.pilot_index import PilotHit, apply_statut_weights, indexed_text


def _hit(chunk: str, score: float, statut: str) -> PilotHit:
	return PilotHit(id_chunk=chunk, source_file="", texte="", score=score, statut_version=statut, annee=None, payload={})


def test_replaced_edition_falls_behind_current_one() -> None:
	hits = [_hit("cdpf2023", 0.50, "remplacee"), _hit("cdpf2025", 0.40, "en_vigueur"), _hit("note", 0.45, "texte_date")]
	ordered = [h.id_chunk for h in apply_statut_weights(hits)]
	assert ordered == ["cdpf2025", "note", "cdpf2023"]


def test_indexed_text_puts_context_and_section_before_text() -> None:
	text = indexed_text({"contexte": "CDPF 2025, sanctions.", "section": "TITRE III"}, "Article 81 ...")
	assert text.splitlines() == ["CDPF 2025, sanctions.", "TITRE III", "Article 81 ..."]


def test_indexed_text_without_enrichment_is_original_text() -> None:
	assert indexed_text({}, "Article 81 ...") == "Article 81 ..."
