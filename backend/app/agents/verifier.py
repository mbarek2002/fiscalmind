from __future__ import annotations

from dataclasses import dataclass

from backend.app.agents.state import Citation
from backend.app.retrieval.hybrid_search import RetrievedChunk


@dataclass
class VerificationResult:
	status: str
	notes: str
	verified_citations: list[Citation]


def verify_citations(
	*,
	citations: list[Citation],
	legal_results: list[RetrievedChunk],
	expected_language: str,
) -> VerificationResult:
	if not citations:
		return VerificationResult(
			status="rejected",
			notes="No citations were produced by synthesis",
			verified_citations=[],
		)

	by_article_id = {item.article_id: item for item in legal_results}
	verified: list[Citation] = []
	reasons: list[str] = []

	for index, citation in enumerate(citations, start=1):
		article_id = citation.get("article_id", "")
		source = by_article_id.get(article_id)
		if source is None:
			reasons.append(f"citation#{index}: article_id not found in retrieved context ({article_id})")
			continue

		if source.statut != "en_vigueur":
			reasons.append(f"citation#{index}: source article is not en_vigueur ({source.statut})")
			continue

		if citation.get("statut") != source.statut:
			reasons.append(
				f"citation#{index}: statut mismatch (citation={citation.get('statut')} source={source.statut})"
			)
			continue

		if citation.get("langue") != expected_language:
			reasons.append(
				f"citation#{index}: language mismatch (citation={citation.get('langue')} expected={expected_language})"
			)
			continue

		if citation.get("numero_article") != source.numero_article:
			reasons.append(
				"citation#"
				f"{index}: numero_article mismatch (citation={citation.get('numero_article')} source={source.numero_article})"
			)
			continue

		extrait = (citation.get("extrait") or "").strip()
		if not extrait:
			reasons.append(f"citation#{index}: empty extrait")
			continue

		verified.append(citation)

	if reasons:
		return VerificationResult(
			status="rejected",
			notes="; ".join(reasons),
			verified_citations=verified,
		)

	return VerificationResult(
		status="validated",
		notes="All citations validated against retrieval context",
		verified_citations=verified,
	)
