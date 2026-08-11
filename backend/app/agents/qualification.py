from backend.app.retrieval.hybrid_search import RetrievedChunk


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
