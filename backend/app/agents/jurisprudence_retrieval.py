from __future__ import annotations

from backend.app.core.config import get_settings
from backend.app.retrieval.hybrid_search import JurisprudenceChunk
from backend.app.retrieval.qdrant_client import search_qdrant_jurisprudence_hybrid
from backend.app.retrieval.rerank import rerank_chunks


def retrieve_jurisprudence_candidates(
	question: str, language: str = "fr", top_k: int = 2
) -> list[JurisprudenceChunk]:
	settings = get_settings()
	candidate_k = max(top_k * max(settings.reranker_candidate_multiplier, 1), top_k)
	rows = search_qdrant_jurisprudence_hybrid(question=question, language=language, top_k=candidate_k)

	return [
		JurisprudenceChunk(
			case_id=row["case_id"],
			reference=row["reference"],
			resume=row["resume"],
			langue=row["langue"],
			categorie=row.get("categorie", "non_classe"),
			dense_score=float(row.get("dense_score", 0.0)),
			sparse_score=float(row.get("sparse_score", 0.0)),
			fused_score=float(row.get("fused_score", 0.0)),
		)
		for row in rows
	]


def retrieve_jurisprudence(question: str, language: str = "fr", top_k: int = 2) -> list[JurisprudenceChunk]:
	"""Hybrid search + rerank over the jurisprudence collection.

	Returns an empty list when no matching case law is indexed rather than
	inventing examples, consistent with the anti-hallucination stance of the
	verifier agent.
	"""
	candidates = retrieve_jurisprudence_candidates(question=question, language=language, top_k=top_k)
	return rerank_chunks(question=question, chunks=candidates, top_k=top_k)
