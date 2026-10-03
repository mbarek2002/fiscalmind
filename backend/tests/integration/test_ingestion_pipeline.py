from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.ingestion import pipeline
from backend.app.models.db_models import DocumentMetadata
from backend.app.retrieval.qdrant_client import search_qdrant_hybrid


class _FakeMinioClient:
	def head_bucket(self, Bucket: str) -> None:
		return None

	def create_bucket(self, Bucket: str) -> None:
		return None

	def upload_file(self, filename: str, bucket: str, key: str) -> None:
		return None


class _FakeQdrantClient:
	def __init__(self, *args, **kwargs) -> None:
		self._points = []

	def collection_exists(self, name: str) -> bool:
		return True

	def create_collection(self, **kwargs) -> None:
		return None

	def upsert(self, collection_name: str, points: list) -> None:
		self._points = points

	def query_points(self, collection_name: str, query, query_filter=None, prefetch=None, using=None, limit: int = 10, with_payload: bool = True):
		class _Point:
			def __init__(self) -> None:
				self.score = 0.85
				self.payload = {
					"id_chunk": "doc-1",
					"loi": "Loi de Finance 2024",
					"numero_article": 12,
					"statut": "en_vigueur",
					"langue": "fr",
					"texte": "TVA et obligations declaratives.",
					"categorie_infraction": ["fraude_fiscale_tva"],
				}

		class _Response:
			points = [_Point()]

		return _Response()


@pytest.mark.asyncio
async def test_ingestion_persists_document_metadata(tmp_path, monkeypatch):
	data_dir = tmp_path / "docs"
	data_dir.mkdir(parents=True, exist_ok=True)
	(data_dir / "lf2024_art12_fr.txt").write_text("Article 12 sur la TVA.", encoding="utf-8")

	monkeypatch.setattr(pipeline, "_build_minio_client", lambda: _FakeMinioClient())
	monkeypatch.setattr(pipeline, "_index_in_qdrant", lambda document, text: None)
	monkeypatch.setattr(pipeline, "_index_in_neo4j", lambda document: None)

	result = await pipeline.ingest_source_directory(str(data_dir), source_type="loi")
	assert result.total_files == 1
	assert result.indexed_files == 1
	assert result.errors == []

	async with pipeline.AsyncSessionLocal() as session:
		rows = (await session.execute(select(DocumentMetadata))).scalars().all()
		assert any(row.numero_article == 12 and row.annee_loi == 2024 for row in rows)


class _FakeEmbeddingClient:
	def embed_text(self, text: str) -> list[float]:
		return [0.1, 0.2, 0.3]

	def embed_hybrid(self, text: str):  # noqa: ANN201
		from backend.app.llm.interfaces import EmbeddingResult

		return EmbeddingResult(dense=[0.1, 0.2, 0.3], sparse=None)


def test_qdrant_real_search_shape(monkeypatch):
	from backend.app.retrieval import qdrant_client as qdrant_module

	monkeypatch.setattr(qdrant_module, "QdrantClient", _FakeQdrantClient)
	# Avoid pulling down the real local embedding model (BGE-M3, multi-GB) over the network.
	monkeypatch.setattr(qdrant_module, "get_embedding_client", lambda: _FakeEmbeddingClient())

	results = search_qdrant_hybrid("Quelle est la sanction TVA ?", language="fr", top_k=1)
	assert len(results) == 1
	assert results[0]["article_id"] == "doc-1"
	assert "fused_score" in results[0]
