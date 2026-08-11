from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.app.core.config import Settings
from backend.app.retrieval.hybrid_search import RetrievedChunk


def _settings(*, strict: bool) -> Settings:
	return Settings(
		database_url="sqlite+aiosqlite:///./test_strict_mode.db",
		environment="dev",
		strict_provider_mode=strict,
		qdrant_url="http://qdrant.local",
	)


class _FailingEmbeddingClient:
	def embed_text(self, _text: str) -> list[float]:
		raise RuntimeError("embedding down")


class _FailingLLMClient:
	def generate(self, prompt: str, system_prompt: str | None = None) -> str:
		raise RuntimeError("llm down")


class _Point:
	def __init__(self, payload: dict, score: float = 0.5) -> None:
		self.payload = payload
		self.score = score


class _DummyQdrantClient:
	last_query_vector: list[float] | None = None
	last_upsert_vector: list[float] | None = None

	def __init__(self, url: str, api_key: str | None = None) -> None:
		self.url = url
		self.api_key = api_key

	def collection_exists(self, _collection_name: str) -> bool:
		return True

	def create_collection(self, *args, **kwargs) -> None:  # noqa: ANN002,ANN003
		return None

	def search(self, collection_name: str, query_vector: list[float], query_filter, limit: int):  # noqa: ANN001
		_DummyQdrantClient.last_query_vector = query_vector
		return [
			_Point(
				payload={
					"id_chunk": "lf2023_art45_fr",
					"loi": "Loi de Finance 2023",
					"numero_article": 45,
					"statut": "en_vigueur",
					"langue": "fr",
					"texte": "Sanction TVA ...",
					"categorie_infraction": ["fraude_fiscale_tva"],
				},
				score=0.9,
			)
		]

	def upsert(self, collection_name: str, points: list) -> None:  # noqa: ANN001
		_DummyQdrantClient.last_upsert_vector = points[0].vector


def test_synthesis_non_strict_uses_fallback_when_llm_fails(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.agents import synthesis as synthesis_mod

	monkeypatch.setattr(synthesis_mod, "get_settings", lambda: _settings(strict=False))
	monkeypatch.setattr(synthesis_mod, "get_llm_client", lambda: _FailingLLMClient())

	answer, citations = synthesis_mod.synthesize_answer(
		question="Quelle sanction TVA ?",
		category="fraude_fiscale_tva",
		language="fr",
		legal_results=[
			RetrievedChunk(
				article_id="lf2023_art45_fr",
				loi="Loi de Finance 2023",
				numero_article=45,
				statut="en_vigueur",
				langue="fr",
				extrait="Extrait article 45",
				category="fraude_fiscale_tva",
			)
		],
		graph_context_ids=["lf2022_art12_fr"],
	)

	assert "Reponse RAG v0 (fallback)." in answer
	assert len(citations) == 1


def test_synthesis_strict_raises_when_llm_fails(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.agents import synthesis as synthesis_mod

	monkeypatch.setattr(synthesis_mod, "get_settings", lambda: _settings(strict=True))
	monkeypatch.setattr(synthesis_mod, "get_llm_client", lambda: _FailingLLMClient())

	with pytest.raises(RuntimeError, match="strict provider mode is enabled"):
		synthesis_mod.synthesize_answer(
			question="Quelle sanction TVA ?",
			category="fraude_fiscale_tva",
			language="fr",
			legal_results=[],
			graph_context_ids=[],
		)


def test_qdrant_non_strict_falls_back_to_deterministic_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.retrieval import qdrant_client as qdrant_mod

	monkeypatch.setattr(qdrant_mod, "get_settings", lambda: _settings(strict=False))
	monkeypatch.setattr(qdrant_mod, "QdrantClient", _DummyQdrantClient)
	monkeypatch.setattr(qdrant_mod, "get_embedding_client", lambda: _FailingEmbeddingClient())
	monkeypatch.setattr(qdrant_mod, "deterministic_embedding", lambda text, size: [0.25, 0.75])

	rows = qdrant_mod.search_qdrant_hybrid("question test", language="fr", top_k=1)

	assert len(rows) == 1
	assert _DummyQdrantClient.last_query_vector == [0.25, 0.75]


def test_qdrant_strict_raises_when_embedding_provider_fails(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.retrieval import qdrant_client as qdrant_mod

	monkeypatch.setattr(qdrant_mod, "get_settings", lambda: _settings(strict=True))
	monkeypatch.setattr(qdrant_mod, "QdrantClient", _DummyQdrantClient)
	monkeypatch.setattr(qdrant_mod, "get_embedding_client", lambda: _FailingEmbeddingClient())

	with pytest.raises(RuntimeError, match="strict provider mode is enabled"):
		qdrant_mod.search_qdrant_hybrid("question test", language="fr", top_k=1)


def _build_document() -> SimpleNamespace:
	return SimpleNamespace(
		id="doc-1",
		titre="Loi de Finance 2023",
		annee_loi=2023,
		numero_article=45,
		langue="fr",
		statut=SimpleNamespace(value="en_vigueur"),
		categorie_infraction=["fraude_fiscale_tva"],
	)


def test_ingestion_non_strict_falls_back_to_deterministic_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.ingestion import pipeline as pipeline_mod

	monkeypatch.setattr(pipeline_mod, "get_settings", lambda: _settings(strict=False))
	monkeypatch.setattr(pipeline_mod, "QdrantClient", _DummyQdrantClient)
	monkeypatch.setattr(pipeline_mod, "get_embedding_client", lambda: _FailingEmbeddingClient())
	monkeypatch.setattr(pipeline_mod, "deterministic_embedding", lambda text, size: [0.1, 0.9])

	pipeline_mod._index_in_qdrant(_build_document(), "texte indexe")

	assert _DummyQdrantClient.last_upsert_vector == [0.1, 0.9]


def test_ingestion_strict_raises_when_embedding_provider_fails(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.ingestion import pipeline as pipeline_mod

	monkeypatch.setattr(pipeline_mod, "get_settings", lambda: _settings(strict=True))
	monkeypatch.setattr(pipeline_mod, "QdrantClient", _DummyQdrantClient)
	monkeypatch.setattr(pipeline_mod, "get_embedding_client", lambda: _FailingEmbeddingClient())

	with pytest.raises(RuntimeError, match="strict provider mode is enabled"):
		pipeline_mod._index_in_qdrant(_build_document(), "texte indexe")
