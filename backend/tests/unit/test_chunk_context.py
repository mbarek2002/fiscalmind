from __future__ import annotations

from backend.app.enrichment.chunk_context import article_in_text, enrich_chunk, rule_context, validate_enrichment

FICHE = {
	"fichier": "cdpf-2025.pdf", "titre": "CODE DES DROITS ET PROCEDURES FISCAUX", "famille": "CDPF",
	"type_document": "code", "annee": 2025, "statut_version": "en_vigueur", "plan": ["TITRE III - SANCTIONS FISCALES"],
}
CHUNK = (
	"Article 80 septies Les juges d'instruction peuvent ... TITRE III – SANCTIONS FISCALES "
	"Article 81 Tout retard dans le paiement de l'impôt entraîne l'application d'une pénalité de retard "
	"liquidée au taux de 1,25% du montant de l'impôt par mois ou fraction de mois de retard."
)


def test_article_in_text_handles_suffix_and_rejects_absent() -> None:
	assert article_in_text("81", CHUNK)
	assert article_in_text("80 septies", CHUNK)
	assert not article_in_text("82", CHUNK)


def test_validate_keeps_proven_values_and_rejects_others() -> None:
	raw = {
		"contexte": "Article 81 du CDPF 2025, Titre III : penalites de retard.",
		"articles_contenus": ["80 septies", "81", "83 ter"],
		"taux_seuils": [
			{"valeur": "1,25%", "description": "penalite mensuelle", "preuve": "liquidée au taux de 1,25% du montant de l'impôt"},
			{"valeur": "3%", "description": "penalite fixe", "preuve": "taux de 3% invente"},
		],
		"impots": ["procedures_sanctions", "inconnu"],
		"infractions": ["retard_paiement"],
		"role": "contribuable",
	}
	values, rejects = validate_enrichment(raw, CHUNK, FICHE)
	assert values["contexte_source"] == "llm"
	assert values["articles_contenus"] == ["80 septies", "81"]
	assert [t["valeur"] for t in values["taux_seuils"]] == ["1,25%"]
	assert values["impots"] == ["procedures_sanctions"]
	assert any("83 ter" in r for r in rejects)
	assert any("3%" in r for r in rejects)


def test_context_with_invented_number_falls_back_to_rule() -> None:
	raw = {"contexte": "Penalite de 5% prevue par la LF 2019."}
	values, rejects = validate_enrichment(raw, CHUNK, FICHE)
	assert values["contexte_source"] == "regle"
	assert values["contexte"] == rule_context(FICHE)
	assert rejects and "contexte" in rejects[0]


def test_llm_failure_gives_rule_context_and_document_metadata() -> None:
	e = enrich_chunk("cdpf-2025.pdf::chunk49", CHUNK, FICHE, raw=None)
	assert not e.llm_ok
	assert e.contexte_source == "regle"
	assert e.annee == 2025 and e.statut_version == "en_vigueur"
