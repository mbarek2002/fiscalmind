from __future__ import annotations

from backend.app.enrichment.document_rules import extract_rule_facts, famille_from_filename
from backend.app.enrichment.versions import compute_version_status


def test_famille_from_filename() -> None:
	assert famille_from_filename("cdpf-2025.pdf") == ("CDPF", "code")
	assert famille_from_filename("Code-des-droits-et-procedures-fiscaux-Janvier-2018.pdf") == ("CDPF", "code")
	assert famille_from_filename("Code-de-limpot-sur-le-revenu-des-personnes-physiques-2021.pdf")[0] == "IRPP-IS"
	assert famille_from_filename("Loi-de-Finances-complementaire-2014.pdf") == ("LF", "loi_finances_complementaire")
	assert famille_from_filename("Note-Commune-N°10.pdf") == ("NOTE_COMMUNE", "note_commune")
	assert famille_from_filename("PORTUGAL.pdf") == ("AUTRE", "autre")


def test_code_year_comes_from_filename() -> None:
	facts = extract_rule_facts("cdpf-2025.pdf", "CODE DES DROITS ... loi n° 2000-82", "")
	assert facts.annee == 2025
	assert facts.annee_source == "nom_fichier"


def test_note_commune_reference_and_year_from_first_page() -> None:
	facts = extract_rule_facts("Note-Commune-N°10.pdf", "Note Commune N° 10 / 2023  \nObjet : Commentaire ...", "")
	assert facts.reference == "Note commune N°10/2023"
	assert facts.annee == 2023
	assert facts.annee_source == "premiere_page"


def test_convention_year_from_signature_on_last_page() -> None:
	facts = extract_rule_facts("France.pdf", "CONVENTION ENTRE LA TUNISIE ET LA FRANCE", "Fait à Tunis, le 28 mai 1973. Pour le Gouvernement")
	assert facts.annee == 1973
	assert facts.annee_source == "derniere_page"


def test_unknown_year_stays_none() -> None:
	facts = extract_rule_facts("11.pdf", "texte sans date", "fin")
	assert facts.annee is None


def test_version_status_latest_edition_is_in_force() -> None:
	files = [
		"Code-des-droits-et-procedures-fiscaux-Janvier-2018.pdf",
		"Code-des-droits-et-procedures-fiscaux-2024.pdf",
		"cdpf-2025.pdf",
		"Note-Commune-N°10.pdf",
		"PORTUGAL.pdf",
	]
	status = compute_version_status(files)
	assert status["cdpf-2025.pdf"].statut_version == "en_vigueur"
	assert status["Code-des-droits-et-procedures-fiscaux-2024.pdf"].statut_version == "remplacee"
	assert status["Code-des-droits-et-procedures-fiscaux-2024.pdf"].remplacee_par == "cdpf-2025.pdf"
	assert status["Note-Commune-N°10.pdf"].statut_version == "texte_date"
	assert status["PORTUGAL.pdf"].statut_version == "indetermine"
