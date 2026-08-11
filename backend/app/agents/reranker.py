from __future__ import annotations

from backend.app.retrieval.hybrid_search import RetrievedChunk
from backend.app.retrieval.rerank import rerank_chunks


def rerank_legal_results(
	question: str,
	legal_candidates: list[RetrievedChunk],
	top_k: int = 3,
) -> list[RetrievedChunk]:
	"""Agent node wrapper that reranks legal candidates using the retrieval reranker."""
	return rerank_chunks(question=question, chunks=legal_candidates, top_k=top_k)
