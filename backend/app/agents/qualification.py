from __future__ import annotations

import re
from datetime import date

from backend.app.retrieval.hybrid_search import RetrievedChunk


_DATE_PATTERN = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
_YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")


def qualify_question(question: str, legal_results: list[RetrievedChunk]) -> str:
	if legal_results:
		return legal_results[0].category

	text = question.lower()

	if "tva" in text:
		return "fraude_fiscale_tva"
	if "is" in text or "impot" in text or "impot" in text:
		return "fraude_fiscale"
	if "douane" in text or "contrebande" in text:
		return "contrebande_douaniere"

	return "non_classe"


def extract_date_des_faits(question: str, *, today: date | None = None) -> date:
	"""Best-effort extraction of the facts' date for temporal (non-retroactivity) filtering.

	Falls back to the query date when the user does not specify one, as
	documented in ARCHITECTURE.md section 5.1.
	"""
	reference = today or date.today()

	date_match = _DATE_PATTERN.search(question)
	if date_match:
		day, month, year = (int(part) for part in date_match.groups())
		try:
			return date(year, month, day)
		except ValueError:
			pass

	year_match = _YEAR_PATTERN.search(question)
	if year_match:
		year = int(year_match.group())
		return date(year, 1, 1)

	return reference
