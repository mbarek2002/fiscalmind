from backend.app.agents.verifier import verify_citations
from backend.app.retrieval.hybrid_search import RetrievedChunk


def _retrieved_chunk() -> RetrievedChunk:
	return RetrievedChunk(
		article_id="lf2023_art45_fr",
		loi="Loi de Finance 2023",
		numero_article=45,
		statut="en_vigueur",
		langue="fr",
		extrait="Sanction en cas de non declaration TVA",
		category="fraude_fiscale_tva",
	)


def test_verifier_validates_matching_citation() -> None:
	result = verify_citations(
		citations=[
			{
				"article_id": "lf2023_art45_fr",
				"loi": "Loi de Finance 2023",
				"numero_article": 45,
				"statut": "en_vigueur",
				"langue": "fr",
				"extrait": "Sanction en cas de non declaration TVA",
			}
		],
		legal_results=[_retrieved_chunk()],
		expected_language="fr",
	)

	assert result.status == "validated"
	assert len(result.verified_citations) == 1
	assert "validated" in result.notes.lower()


def test_verifier_rejects_when_article_not_found() -> None:
	result = verify_citations(
		citations=[
			{
				"article_id": "unknown",
				"loi": "Loi de Finance 2023",
				"numero_article": 45,
				"statut": "en_vigueur",
				"langue": "fr",
				"extrait": "...",
			}
		],
		legal_results=[_retrieved_chunk()],
		expected_language="fr",
	)

	assert result.status == "rejected"
	assert result.verified_citations == []
	assert "not found" in result.notes.lower()


def test_verifier_rejects_non_en_vigueur_source() -> None:
	chunk = _retrieved_chunk()
	chunk.statut = "abroge"

	result = verify_citations(
		citations=[
			{
				"article_id": "lf2023_art45_fr",
				"loi": "Loi de Finance 2023",
				"numero_article": 45,
				"statut": "abroge",
				"langue": "fr",
				"extrait": "...",
			}
		],
		legal_results=[chunk],
		expected_language="fr",
	)

	assert result.status == "rejected"
	assert "not en_vigueur" in result.notes.lower()


def test_verifier_rejects_language_mismatch() -> None:
	result = verify_citations(
		citations=[
			{
				"article_id": "lf2023_art45_fr",
				"loi": "Loi de Finance 2023",
				"numero_article": 45,
				"statut": "en_vigueur",
				"langue": "ar",
				"extrait": "...",
			}
		],
		legal_results=[_retrieved_chunk()],
		expected_language="fr",
	)

	assert result.status == "rejected"
	assert "language mismatch" in result.notes.lower()


def test_verifier_rejects_empty_citations() -> None:
	result = verify_citations(citations=[], legal_results=[_retrieved_chunk()], expected_language="fr")

	assert result.status == "rejected"
	assert "no citations" in result.notes.lower()
