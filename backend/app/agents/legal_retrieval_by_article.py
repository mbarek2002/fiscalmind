from __future__ import annotations

from backend.app.ingestion.indexing_by_article import search_by_article_hybrid
from backend.app.retrieval.hybrid_search import RetrievedChunk


def retrieve_legal_candidates_by_article(question: str, language: str = "fr", top_k: int = 3) -> list[RetrievedChunk]:
	"""Adaptateur pour le pipeline by-article : qualify_question()/synthesize_answer()/
	verify_citations() (backend/app/agents/*.py, inchanges) attendent tous des
	RetrievedChunk -- ce module convertit la sortie de search_by_article_hybrid()
	(ArticleSearchResult) vers ce type commun pour les reutiliser sans les modifier."""
	results = search_by_article_hybrid(question=question, language=language, top_k=top_k)

	return [
		RetrievedChunk(
			article_id=r.id_chunk,
			loi=r.source_file,
			# RetrievedChunk.numero_article est un int non-optionnel (contrainte heritee
			# de l'ancien pipeline) -- 0 signifie "non determine", meme convention que
			# legal_retrieval.py pour les chunks sans numero d'article detecte.
			numero_article=r.numero_article if r.numero_article is not None else 0,
			statut=r.statut,
			langue=r.langue,
			extrait=r.texte,
			category=r.category,
			dense_score=r.score,
			sparse_score=0.0,
			fused_score=r.score,
		)
		for r in results
	]
