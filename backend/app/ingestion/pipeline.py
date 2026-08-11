from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.db.session import AsyncSessionLocal
from backend.app.llm.factory import get_embedding_client
from backend.app.models.db_models import DocumentMetadata
from backend.app.models.enums import DocumentSourceType, DocumentStatus
from backend.app.retrieval.hybrid_search import deterministic_embedding


FILENAME_PATTERN = re.compile(r"lf(?P<year>\d{4})_art(?P<article>\d+?)_(?P<lang>fr|ar)", re.IGNORECASE)


@dataclass
class IngestionResult:
	total_files: int
	indexed_files: int
	errors: list[str]


def _infer_metadata_from_filename(file_path: Path) -> tuple[int | None, int | None, str]:
	match = FILENAME_PATTERN.search(file_path.stem)
	if not match:
		return None, None, "fr"
	return int(match.group("year")), int(match.group("article")), match.group("lang").lower()


def _load_text(file_path: Path) -> str:
	content = file_path.read_text(encoding="utf-8", errors="ignore")
	return content.strip()


def _build_minio_client():
	settings = get_settings()
	if not settings.minio_endpoint or not settings.minio_access_key or not settings.minio_secret_key:
		return None

	return boto3.client(
		"s3",
		endpoint_url=settings.minio_endpoint,
		aws_access_key_id=settings.minio_access_key,
		aws_secret_access_key=settings.minio_secret_key,
	)


def _ensure_bucket(client, bucket_name: str) -> None:
	try:
		client.head_bucket(Bucket=bucket_name)
	except ClientError:
		client.create_bucket(Bucket=bucket_name)


def _upload_to_minio(client, bucket_name: str, object_key: str, file_path: Path) -> str:
	client.upload_file(str(file_path), bucket_name, object_key)
	return f"s3://{bucket_name}/{object_key}"


def _index_in_qdrant(document: DocumentMetadata, text: str) -> None:
	settings = get_settings()
	if not settings.qdrant_url:
		return

	client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
	collection_name = settings.qdrant_collection_loi
	if not client.collection_exists(collection_name):
		client.create_collection(
			collection_name=collection_name,
			vectors_config=VectorParams(size=settings.qdrant_vector_size, distance=Distance.COSINE),
		)

	try:
		vector = get_embedding_client().embed_text(text)
	except Exception as exc:
		if settings.provider_strict_mode_enabled:
			raise RuntimeError(
				"Embedding provider is unavailable during ingestion while strict provider mode is enabled"
			) from exc
		vector = deterministic_embedding(text, settings.qdrant_vector_size)
	point = PointStruct(
		id=document.id,
		vector=vector,
		payload={
			"id_chunk": document.id,
			"document_id": document.id,
			"loi": document.titre,
			"annee_loi": document.annee_loi,
			"numero_article": document.numero_article,
			"langue": document.langue,
			"statut": document.statut.value,
			"categorie_infraction": document.categorie_infraction,
			"texte": text,
		},
	)
	client.upsert(collection_name=collection_name, points=[point])


def _index_in_neo4j(document: DocumentMetadata) -> None:
	settings = get_settings()
	if not settings.neo4j_uri or not settings.neo4j_username or not settings.neo4j_password:
		return

	driver = GraphDatabase.driver(
		settings.neo4j_uri,
		auth=(settings.neo4j_username, settings.neo4j_password),
	)
	try:
		with driver.session() as session:
			session.run(
				"""
				MERGE (a:Article {id: $id})
				SET a.numero = $numero_article,
				    a.annee_loi = $annee_loi,
				    a.langue = $langue,
				    a.statut = $statut
				WITH a
				MERGE (l:Loi {nom: $loi, annee: $annee_loi})
				MERGE (a)-[:APPARTIENT_A]->(l)
				""",
				id=document.id,
				numero_article=document.numero_article,
				annee_loi=document.annee_loi,
				langue=document.langue,
				statut=document.statut.value,
				loi=document.titre,
			)
	finally:
		driver.close()


async def _persist_document_metadata(
	session: AsyncSession,
	*,
	source_type: DocumentSourceType,
	title: str,
	annee_loi: int | None,
	numero_article: int | None,
	langue: str,
	storage_path: str,
) -> DocumentMetadata:
	document = DocumentMetadata(
		source_type=source_type,
		titre=title,
		annee_loi=annee_loi,
		numero_article=numero_article,
		langue=langue,
		statut=DocumentStatus.en_vigueur,
		date_entree_vigueur=datetime.now(UTC).date(),
		categorie_infraction=["non_classe"],
		storage_path=storage_path,
		anonymized=source_type == DocumentSourceType.jurisprudence,
	)
	session.add(document)
	await session.commit()
	await session.refresh(document)
	return document


async def ingest_source_directory(source_dir: str, source_type: str = "loi") -> IngestionResult:
	base_dir = Path(source_dir)
	if not base_dir.exists():
		return IngestionResult(total_files=0, indexed_files=0, errors=[f"Source directory not found: {source_dir}"])

	supported_files = [
		path for path in base_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".txt", ".md"}
	]
	result = IngestionResult(total_files=len(supported_files), indexed_files=0, errors=[])

	minio_client = _build_minio_client()
	settings = get_settings()
	if minio_client is not None:
		_ensure_bucket(minio_client, settings.minio_bucket_raw)

	source_enum = DocumentSourceType(source_type)

	async with AsyncSessionLocal() as session:
		for file_path in supported_files:
			try:
				text = _load_text(file_path)
				if not text:
					result.errors.append(f"Empty document: {file_path}")
					continue

				annee_loi, numero_article, langue = _infer_metadata_from_filename(file_path)
				object_key = f"{source_enum.value}/{datetime.now(UTC).strftime('%Y%m%d')}/{file_path.name}"

				if minio_client is not None:
					storage_path = _upload_to_minio(minio_client, settings.minio_bucket_raw, object_key, file_path)
				else:
					storage_path = str(file_path)

				document = await _persist_document_metadata(
					session,
					source_type=source_enum,
					title=f"Loi de Finance {annee_loi}" if annee_loi else file_path.stem,
					annee_loi=annee_loi,
					numero_article=numero_article,
					langue=langue,
					storage_path=storage_path,
				)

				_index_in_qdrant(document, text)
				_index_in_neo4j(document)
				result.indexed_files += 1
			except Exception as exc:
				result.errors.append(f"{file_path}: {exc}")

	return result


def ingest_source_directory_sync(source_dir: str, source_type: str = "loi") -> IngestionResult:
	return asyncio.run(ingest_source_directory(source_dir=source_dir, source_type=source_type))
