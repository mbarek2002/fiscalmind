from backend.app.agents import legal_retrieval_by_article
from backend.app.ingestion.indexing_by_article import ArticleSearchResult


def test_retrieve_legal_candidates_by_article_converts_to_retrieved_chunk(monkeypatch) -> None:
	def fake_search(question, language, top_k):
		return [
			ArticleSearchResult(
				id_chunk="f.pdf::chunk3",
				source_file="f.pdf",
				numero_article=12,
				langue="fr",
				texte="Texte de l'article 12.",
				score=0.91,
				statut="en_vigueur",
				category="non_classe",
			)
		]

	monkeypatch.setattr(legal_retrieval_by_article, "search_by_article_hybrid", fake_search)

	results = legal_retrieval_by_article.retrieve_legal_candidates_by_article(question="Q ?", language="fr", top_k=3)

	assert len(results) == 1
	chunk = results[0]
	assert chunk.article_id == "f.pdf::chunk3"
	assert chunk.loi == "f.pdf"
	assert chunk.numero_article == 12
	assert chunk.statut == "en_vigueur"
	assert chunk.langue == "fr"
	assert chunk.extrait == "Texte de l'article 12."
	assert chunk.category == "non_classe"
	assert chunk.dense_score == 0.91
	assert chunk.fused_score == 0.91


def test_retrieve_legal_candidates_by_article_defaults_missing_numero_article_to_zero(monkeypatch) -> None:
	def fake_search(question, language, top_k):
		return [
			ArticleSearchResult(
				id_chunk="f.pdf::chunk0",
				source_file="f.pdf",
				numero_article=None,
				langue="fr",
				texte="Note commune sans article propre.",
				score=0.8,
			)
		]

	monkeypatch.setattr(legal_retrieval_by_article, "search_by_article_hybrid", fake_search)

	results = legal_retrieval_by_article.retrieve_legal_candidates_by_article(question="Q ?", language="fr", top_k=3)

	assert results[0].numero_article == 0
