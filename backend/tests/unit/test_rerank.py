from __future__ import annotations

import pytest

from backend.app.core.config import Settings
from backend.app.retrieval.hybrid_search import RetrievedChunk


def _settings(*, strict: bool, provider: str = "local") -> Settings:
	return Settings(
		database_url="sqlite+aiosqlite:///./test_rerank.db",
		environment="dev",
		strict_provider_mode=strict,
		reranker_provider=provider,
	)


def _chunks() -> list[RetrievedChunk]:
	return [
		RetrievedChunk(
			article_id="a1",
			loi="Loi A",
			numero_article=1,
			statut="en_vigueur",
			langue="fr",
			extrait="Texte article un",
			category="x",
			fused_score=0.9,
		),
		RetrievedChunk(
			article_id="a2",
			loi="Loi B",
			numero_article=2,
			statut="en_vigueur",
			langue="fr",
			extrait="Texte article deux",
			category="x",
			fused_score=0.2,
		),
	]


def test_rerank_local_reorders_by_cross_encoder_scores(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.retrieval import rerank as rerank_mod

	monkeypatch.setattr(rerank_mod, "get_settings", lambda: _settings(strict=False, provider="local"))
	monkeypatch.setattr(
		rerank_mod,
		"_score_with_local_cross_encoder",
		lambda question, chunks, settings: [0.1, 0.8],
	)

	ranked = rerank_mod.rerank_chunks("question", _chunks(), top_k=2)

	assert [item.article_id for item in ranked] == ["a2", "a1"]
	assert ranked[0].fused_score == 0.8


def test_rerank_non_strict_falls_back_to_hybrid_order(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.retrieval import rerank as rerank_mod

	monkeypatch.setattr(rerank_mod, "get_settings", lambda: _settings(strict=False, provider="local"))

	def _fail(*args, **kwargs):  # noqa: ANN002,ANN003
		raise RuntimeError("reranker down")

	monkeypatch.setattr(rerank_mod, "_score_with_local_cross_encoder", _fail)

	ranked = rerank_mod.rerank_chunks("question", _chunks(), top_k=2)

	assert [item.article_id for item in ranked] == ["a1", "a2"]


def test_rerank_strict_raises_when_reranker_fails(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.retrieval import rerank as rerank_mod

	monkeypatch.setattr(rerank_mod, "get_settings", lambda: _settings(strict=True, provider="local"))

	def _fail(*args, **kwargs):  # noqa: ANN002,ANN003
		raise RuntimeError("reranker down")

	monkeypatch.setattr(rerank_mod, "_score_with_local_cross_encoder", _fail)

	with pytest.raises(RuntimeError, match="strict provider mode is enabled"):
		rerank_mod.rerank_chunks("question", _chunks(), top_k=2)


def test_rerank_non_local_provider_non_strict_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.retrieval import rerank as rerank_mod

	monkeypatch.setattr(rerank_mod, "get_settings", lambda: _settings(strict=False, provider="openai"))
	ranked = rerank_mod.rerank_chunks("question", _chunks(), top_k=2)

	assert [item.article_id for item in ranked] == ["a1", "a2"]
