from __future__ import annotations

from backend.app.agents.state import Citation, JurisprudenceCitation


_CITOYEN_INTRO = (
	"Voici une explication en langage simple. Ceci ne remplace pas l'avis d'un avocat."
)
_AVOCAT_INTRO = "Analyse juridique avec references precises pour usage professionnel."
_JUGE_INTRO = "Qualification proposee et textes de reference pour appui a la decision."


def _format_legal_citations(citations: list[Citation]) -> str:
	if not citations:
		return "Aucun article n'a pu etre cite avec certitude."
	lines = [
		f"- {item['loi']}, article {item['numero_article']} ({item['statut']}, {item['langue']})"
		for item in citations
	]
	return "\n".join(lines)


def _format_jurisprudence(jurisprudence: list[JurisprudenceCitation]) -> str:
	if not jurisprudence:
		return ""
	lines = [f"- {item['reference']} : {item['resume']}" for item in jurisprudence]
	return "\nJurisprudence similaire :\n" + "\n".join(lines)


def format_answer(
	*,
	answer: str,
	user_role: str,
	citations: list[Citation],
	jurisprudence: list[JurisprudenceCitation],
) -> str:
	"""Adapts the tone/level of detail of the validated answer to the requesting profile.

	The synthesis agent's answer text is never rewritten here (only framed and
	annotated) so the verified, source-grounded content cannot be altered
	post-verification.
	"""
	role = (user_role or "citoyen").lower()

	if role == "citoyen":
		return f"{_CITOYEN_INTRO}\n\n{answer}"

	if role == "juge":
		sections = [
			_JUGE_INTRO,
			"",
			answer,
			"",
			"Textes de reference :",
			_format_legal_citations(citations),
		]
		jurisprudence_block = _format_jurisprudence(jurisprudence)
		if jurisprudence_block:
			sections.append(jurisprudence_block)
		return "\n".join(sections)

	# avocat / admin: full detail with exact citations and case law references
	sections = [
		_AVOCAT_INTRO,
		"",
		answer,
		"",
		"Citations :",
		_format_legal_citations(citations),
	]
	jurisprudence_block = _format_jurisprudence(jurisprudence)
	if jurisprudence_block:
		sections.append(jurisprudence_block)
	return "\n".join(sections)
