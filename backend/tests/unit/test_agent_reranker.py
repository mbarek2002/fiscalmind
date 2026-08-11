from __future__ import annotations

import pytest

from backend.app.retrieval.hybrid_search import RetrievedChunk


def _chunks() -> list[RetrievedChunk]:
	return [
		RetrievedChunk(
			article_id="a1",
			loi="Loi A",
			numero_article=1,
			statut="en_vigueur",
			langue="fr",
			extrait="Texte A",
			category="x",
		),
		RetrievedChunk(
			article_id="a2",
			loi="Loi B",
			numero_article=2,
			statut="en_vigueur",
			langue="fr",
			extrait="Texte B",
			category="x",
		),
	]


def test_reranker_agent_delegates_to_retrieval_rerank(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.agents import reranker as reranker_mod

	def _fake_rerank(question: str, chunks: list[RetrievedChunk], top_k: int | None = None) -> list[RetrievedChunk]:
		assert question == "question test"
		assert top_k == 1
		return [chunks[1]]

	monkeypatch.setattr(reranker_mod, "rerank_chunks", _fake_rerank)

	ranked = reranker_mod.rerank_legal_results(
		question="question test",
		legal_candidates=_chunks(),
		top_k=1,
	)

	assert len(ranked) == 1
	assert ranked[0].article_id == "a2"
