from __future__ import annotations

from backend.app.enrichment.document_fiche import merge_fiche, parse_json_object, validate_llm_fields
from backend.app.enrichment.document_rules import RuleFacts
from backend.app.enrichment.versions import VersionStatus

DOC = "Note Commune N° 10 / 2023\nObjet : Commentaire des dispositions de l'article 60 du décret-loi n°2022-79 portant loi de finances pour l'année 2023"


def test_parse_json_object_tolerates_fences() -> None:
	assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_field_kept_only_with_proof_found_in_text() -> None:
	raw = {
		"reference": {"valeur": "Note commune N°10/2023", "preuve": "Note Commune N° 10 / 2023"},
		"titre": {"valeur": "Titre invente", "preuve": "phrase absente du document"},
	}
	values, proofs, rejects = validate_llm_fields(raw, DOC)
	assert values == {"reference": "Note commune N°10/2023"}
	assert "reference" in proofs
	assert any(r.startswith("titre") for r in rejects)


def test_year_rejected_when_absent_from_proof() -> None:
	raw = {"annee": {"valeur": 2024, "preuve": "Note Commune N° 10 / 2023"}}
	values, _, rejects = validate_llm_fields(raw, DOC)
	assert "annee" not in values
	assert rejects and "2024" in rejects[0]


def test_rules_win_over_llm_on_year_and_conflict_is_recorded() -> None:
	rules = RuleFacts(famille="NOTE_COMMUNE", type_document="note_commune", annee=2023, annee_source="premiere_page", reference="Note commune N°10/2023")
	raw = {
		"annee": {"valeur": 2022, "preuve": "décret-loi n°2022-79"},
		"type_document": "note_commune",
		"impots_concernes": ["TVA", "inconnu"],
	}
	fiche = merge_fiche("Note-Commune-N°10.pdf", rules, VersionStatus("texte_date"), raw, DOC, nb_chunks=8)
	assert fiche.annee == 2023
	assert fiche.conflits and "llm=2022" in fiche.conflits[0]
	assert fiche.impots_concernes == ["TVA"]
	assert fiche.statut_version == "texte_date"


def test_proof_matching_ignores_accents() -> None:
	raw = {"annee": {"valeur": 1999, "preuve": "FAIT A Lisbonne, le 24 fevrier 1999"}}
	values, _, rejects = validate_llm_fields(raw, "Fait à Lisbonne, le 24 février 1999.")
	assert values == {"annee": 1999} and not rejects


def test_unnamed_file_reclassified_as_code_from_title() -> None:
	rules = RuleFacts(famille="AUTRE", type_document="autre", annee=2001, annee_source="premiere_page")
	text = "CODE DE L'IMPOT SUR LE REVENU DES PERSONNES PHYSIQUES ET DE L'IMPOT SUR LES SOCIETES promulgue par la loi n°2001-83"
	raw = {"titre": {"valeur": "CODE DE L'IMPOT SUR LE REVENU DES PERSONNES PHYSIQUES ET DE L'IMPOT SUR LES SOCIETES",
					 "preuve": "CODE DE L'IMPOT SUR LE REVENU DES PERSONNES PHYSIQUES"}}
	fiche = merge_fiche("11.pdf", rules, VersionStatus("indetermine"), raw, text, nb_chunks=20)
	assert fiche.famille == "IRPP-IS"
	assert fiche.type_document == "code"
	assert fiche.annee is None


def test_llm_fills_year_when_rules_have_none() -> None:
	rules = RuleFacts(famille="AUTRE", type_document="autre")
	raw = {"annee": {"valeur": 1973, "preuve": "le 28 mai 1973"}, "type_document": "convention"}
	fiche = merge_fiche("France.pdf", rules, VersionStatus("indetermine"), raw, "Fait à Tunis, le 28 mai 1973.", nb_chunks=20)
	assert fiche.annee == 1973
	assert fiche.annee_source == "llm"
	assert fiche.type_document == "convention"
