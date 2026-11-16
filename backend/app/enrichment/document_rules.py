"""Metadonnees de document extraites par regles (sans LLM).

Prioritaires sur le LLM : gratuites, deterministes et sans invention. Le LLM ne
sert qu'a completer ce que les regles ne trouvent pas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

YEAR = r"(19[5-9]\d|20[0-4]\d)"
MOIS = r"(?:janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[ûu]t|septembre|octobre|novembre|d[ée]cembre)"

# (famille, type_document, motif sur le nom de fichier en minuscules)
FAMILLES: list[tuple[str, str, re.Pattern]] = [
	("CDPF", "code", re.compile(r"^cdpf|droits-et-procedures-fiscaux")),
	("IRPP-IS", "code", re.compile(r"impot-sur-le-revenu|is-et-irpp")),
	("TVA", "code", re.compile(r"valeur-ajoutee")),
	("CDET", "code", re.compile(r"^code.*enregistrement")),
	("FL", "code", re.compile(r"fiscalite-locale")),
	("COMPTA", "code", re.compile(r"^code_compta")),
	("RECUEIL", "recueil", re.compile(r"^recueil")),
	("LF", "loi_finances", re.compile(r"loi-de-finances?")),
	("NOTE_COMMUNE", "note_commune", re.compile(r"^note-?commune")),
]

# Familles de codes : une seule edition "en vigueur" (la plus recente).
FAMILLES_EDITIONS = {"CDPF", "IRPP-IS", "TVA", "CDET", "FL", "RECUEIL"}

NOTE_REF = re.compile(r"Note\s+commune\s+n\s*[°o]?\s*(\d+)\s*/\s*" + YEAR, re.I)
LOI_NUM = re.compile(r"(?:loi|d[ée]cret[- ]loi)\s+n\s*[°o]?\s*" + YEAR + r"\s*-\s*\d+", re.I)
LF_ANNEE = re.compile(r"loi\s+de\s+finances\s+(?:compl[ée]mentaire\s+)?pour\s+l.ann[ée]e\s+" + YEAR, re.I)
DATE_FR = re.compile(r"\d{1,2}(?:er)?\s+" + MOIS + r"\s+" + YEAR, re.I)
FAIT_A = re.compile(r"Fait\s+[àa]\s+[^,\n]{2,40},?\s+le\s+\d{1,2}(?:er)?\s+" + MOIS + r"\s+" + YEAR, re.I)


@dataclass
class RuleFacts:
	famille: str
	type_document: str
	annee: int | None = None
	annee_source: str | None = None  # nom_fichier | premiere_page | derniere_page
	annee_preuve: str | None = None
	reference: str | None = None
	notes: list[str] = field(default_factory=list)


def famille_from_filename(filename: str) -> tuple[str, str]:
	low = filename.lower()
	for famille, type_document, pattern in FAMILLES:
		if pattern.search(low):
			if famille == "LF" and "complementaire" in low:
				return famille, "loi_finances_complementaire"
			return famille, type_document
	return "AUTRE", "autre"


TITRES_CODES: list[tuple[str, re.Pattern]] = [
	("CDPF", re.compile(r"droits\s+et\s+proc[ée]dures\s+fiscaux", re.I)),
	("IRPP-IS", re.compile(r"imp[ôo]t\s+sur\s+le\s+revenu\s+des\s+personnes\s+physiques", re.I)),
	("TVA", re.compile(r"taxe\s+sur\s+la\s+valeur\s+ajout[ée]e", re.I)),
	("CDET", re.compile(r"droits\s+d.enregistrement\s+et\s+de\s+timbre", re.I)),
	("FL", re.compile(r"fiscalit[ée]\s+locale", re.I)),
]


def code_famille_from_title(title: str | None) -> str | None:
	"""Famille d'un code reconnue a son titre ("CODE DE L'IMPOT SUR LE REVENU ...")."""
	if not title or not re.match(r"\s*code\b", title, re.I):
		return None
	for famille, pattern in TITRES_CODES:
		if pattern.search(title):
			return famille
	return None


def year_from_filename(filename: str) -> int | None:
	match = re.search(r"(?<!\d)" + YEAR + r"(?!\d)", filename)
	return int(match.group(1)) if match else None


def extract_rule_facts(filename: str, first_page: str, last_page: str) -> RuleFacts:
	famille, type_document = famille_from_filename(filename)
	facts = RuleFacts(famille=famille, type_document=type_document)

	note = NOTE_REF.search(first_page)
	if note:
		facts.reference = f"Note commune N°{note.group(1)}/{note.group(2)}"

	# Ordre de priorite : nom de fichier (codes, lois, recueils), reference de la
	# note, numero de loi, "loi de finances pour l'annee", date, puis "Fait a ..."
	# en derniere page (conventions).
	candidates: list[tuple[str, re.Match | None, str]] = []
	if famille in FAMILLES_EDITIONS or famille == "LF":
		year = year_from_filename(filename)
		if year:
			facts.annee, facts.annee_source, facts.annee_preuve = year, "nom_fichier", filename
			return facts
	candidates += [
		("premiere_page", note, "note"),
		("premiere_page", LOI_NUM.search(first_page), "loi"),
		("premiere_page", LF_ANNEE.search(first_page), "lf"),
		("premiere_page", DATE_FR.search(first_page), "date"),
		("derniere_page", FAIT_A.search(last_page), "fait_a"),
	]
	for source, match, _kind in candidates:
		if match:
			year = int(match.group(match.lastindex))
			facts.annee, facts.annee_source, facts.annee_preuve = year, source, match.group(0)
			return facts

	year = year_from_filename(filename)
	if year:
		facts.annee, facts.annee_source, facts.annee_preuve = year, "nom_fichier", filename
	return facts
