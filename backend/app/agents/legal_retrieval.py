from backend.app.core.config import get_settings
from backend.app.agents.reranker import rerank_legal_results
from backend.app.retrieval.hybrid_search import RetrievedChunk
from backend.app.retrieval.neo4j_client import fetch_related_articles
from backend.app.retrieval.qdrant_client import search_qdrant_hybrid


def retrieve_legal_candidates(question: str, language: str = "fr", top_k: int = 3) -> list[RetrievedChunk]:
	settings = get_settings()
	candidate_k = max(top_k * max(settings.reranker_candidate_multiplier, 1), top_k)
	qdrant_rows = search_qdrant_hybrid(question=question, language=language, top_k=candidate_k)

	return [
		RetrievedChunk(
			article_id=row["article_id"],
			loi=row["loi"],
			# numero_article is None for chunks produced by the markdown-header chunking
			# pipeline (article-number detection is deferred to a later LLM pass, not done at
			# chunking time) — fall back to 0 rather than crashing on int(None).
			numero_article=int(row["numero_article"]) if row.get("numero_article") is not None else 0,
			statut=row["statut"],
			langue=row["langue"],
			extrait=row["extrait"],
			category=row.get("category", "non_classe"),
			dense_score=float(row.get("dense_score", 0.0)),
			sparse_score=float(row.get("sparse_score", 0.0)),
			fused_score=float(row.get("fused_score", 0.0)),
		)
		for row in qdrant_rows
	]


def collect_graph_context_ids(chunks: list[RetrievedChunk]) -> list[str]:
	related_ids: list[str] = []
	for chunk in chunks:
		related_ids.extend(fetch_related_articles(chunk.article_id))
	return sorted(set(related_ids))


def retrieve_legal_articles(question: str, language: str = "fr", top_k: int = 3) -> tuple[list[RetrievedChunk], list[str]]:
	legal_candidates = retrieve_legal_candidates(question=question, language=language, top_k=top_k)
	ranked_chunks = rerank_legal_results(question=question, legal_candidates=legal_candidates, top_k=top_k)
	graph_context_ids = collect_graph_context_ids(ranked_chunks)
	return ranked_chunks, graph_context_ids
