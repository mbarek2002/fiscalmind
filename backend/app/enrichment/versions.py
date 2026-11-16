"""Statut des editions : pour chaque famille de codes, seule l'edition la plus
recente du corpus est "en_vigueur" ; les autres sont "remplacee".

Notes communes et lois de finances ne sont pas des editions consolidees : elles
gardent leur date ("texte_date") car la regle qu'elles decrivent a pu changer
depuis. Ce statut est calcule par regle, jamais par le LLM (il depend de
l'ensemble du corpus, pas d'un seul document).
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.enrichment.document_rules import FAMILLES_EDITIONS, famille_from_filename, year_from_filename


@dataclass
class VersionStatus:
	statut_version: str  # en_vigueur | remplacee | texte_date | indetermine
	remplacee_par: str | None = None


def compute_version_status(all_filenames: list[str]) -> dict[str, VersionStatus]:
	latest: dict[str, tuple[int, str]] = {}
	for f in all_filenames:
		famille, _ = famille_from_filename(f)
		year = year_from_filename(f)
		if famille in FAMILLES_EDITIONS and year is not None:
			if famille not in latest or year > latest[famille][0]:
				latest[famille] = (year, f)

	status: dict[str, VersionStatus] = {}
	for f in all_filenames:
		famille, type_document = famille_from_filename(f)
		year = year_from_filename(f)
		if famille in FAMILLES_EDITIONS:
			if year is None or famille not in latest:
				status[f] = VersionStatus("indetermine")
			elif f == latest[famille][1]:
				status[f] = VersionStatus("en_vigueur")
			else:
				status[f] = VersionStatus("remplacee", remplacee_par=latest[famille][1])
		elif type_document in ("note_commune", "loi_finances", "loi_finances_complementaire"):
			status[f] = VersionStatus("texte_date")
		else:
			status[f] = VersionStatus("indetermine")
	return status
