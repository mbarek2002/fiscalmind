from __future__ import annotations

import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient, models

from backend.app.core.config import get_settings
from backend.app.ingestion.chunking import Chunk
from backend.app.ingestion.embedding_e5 import embed_passages, embed_query


def _get_client() -> QdrantClient:
	settings = get_settings()
	return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def point_id_for_chunk(chunk_id: str) -> str:
	"""Identifiant Qdrant deterministe d'un chunk ("fichier.pdf::chunkN")."""
	return str(uuid.uuid5(uuid.NAMESPACE_OID, chunk_id))


def fetch_document_chunks(source_file: str) -> list[tuple[str, str]]:
	"""(chunk_id, texte) de tous les chunks d'un document, dans l'ordre du document."""
	settings = get_settings()
	client = _get_client()
	flt = models.Filter(must=[models.FieldCondition(key="source_file", match=models.MatchValue(value=source_file))])
	rows: list[tuple[str, str]] = []
	offset = None
	while True:
		points, offset = client.scroll(
			collection_name=settings.qdrant_collection_loi_by_article,
			scroll_filter=flt,
			limit=1000,
			offset=offset,
			with_payload=["id_chunk", "texte"],
			with_vectors=False,
		)
		rows += [(p.payload["id_chunk"], p.payload.get("texte", "")) for p in points]
		if offset is None:
			break
	return sorted(rows, key=lambda r: int(r[0].rsplit("chunk", 1)[-1]))


def list_source_files() -> list[str]:
	"""Noms de tous les documents indexes dans la collection."""
	settings = get_settings()
	client = _get_client()
	files: set[str] = set()
	offset = None
	while True:
		points, offset = client.scroll(
			collection_name=settings.qdrant_collection_loi_by_article,
			limit=2000,
			offset=offset,
			with_payload=["source_file"],
			with_vectors=False,
		)
		files.update(p.payload["source_file"] for p in points)
		if offset is None:
			return sorted(files)


def fetch_chunk_texts(chunk_ids: list[str]) -> dict[str, str]:
	"""Texte indexe des chunks demandes, par chunk_id (absents ignores)."""
	if not chunk_ids:
		return {}
	settings = get_settings()
	points = _get_client().retrieve(
		collection_name=settings.qdrant_collection_loi_by_article,
		ids=[point_id_for_chunk(c) for c in chunk_ids],
		with_payload=True,
	)
	return {p.payload["id_chunk"]: p.payload.get("texte", "") for p in points}


def ensure_collection_by_article() -> None:
	"""Cree la collection separee (si absente) avec un vecteur dense (E5) et un
	index full-text BM25 natif (Qdrant >= 1.20, verifie en conditions reelles) sur
	le champ 'texte' -- remplace le besoin de calculer un vecteur epars soi-meme."""
	settings = get_settings()
	client = _get_client()
	collection_name = settings.qdrant_collection_loi_by_article

	if client.collection_exists(collection_name):
		return

	client.create_collection(
		collection_name=collection_name,
		vectors_config={"dense": models.VectorParams(size=settings.e5_embedding_dim, distance=models.Distance.COSINE)},
	)
	client.create_payload_index(
		collection_name=collection_name,
		field_name="texte",
		field_schema=models.TextIndexParams(
			type=models.TextIndexType.TEXT,
			scoring=models.TextScoringParams(type=models.TextScoringType.BM25),
		),
	)


def index_chunks_by_article(chunks: list[Chunk]) -> None:
	"""Indexe une liste de Chunk (produits par chunk_by_article()) dans la
	collection separee -- n'ecrit jamais dans qdrant_collection_loi (production)."""
	if not chunks:
		return

	ensure_collection_by_article()
	settings = get_settings()
	client = _get_client()

	dense_vectors = embed_passages([chunk.text for chunk in chunks])

	points = [
		models.PointStruct(
			id=point_id_for_chunk(chunk.chunk_id),
			vector={"dense": dense_vector},
			payload={
				"id_chunk": chunk.chunk_id,
				"source_file": chunk.source_file,
				"numero_article": chunk.numero_article,
				"langue": chunk.langue,
				"texte": chunk.text,
				# Pas encore de veritable suivi de statut legal (abroge/modifie) pour ce
				# pipeline -- "en_vigueur" par defaut, meme convention que l'ancien pipeline
				# (documents.py) pour les documents nouvellement indexes.
				"statut": "en_vigueur",
				"category": "non_classe",
				**chunk.headers,
			},
		)
		for chunk, dense_vector in zip(chunks, dense_vectors)
	]

	client.upsert(collection_name=settings.qdrant_collection_loi_by_article, points=points)


def get_top_dense_score(question: str, language: str = "fr") -> float:
	"""Score de similarite cosinus brut (dense seul, pas de fusion RRF) pour le
	meilleur resultat. Sert de signal de confiance absolu -- contrairement au
	score RRF renvoye par search_by_article_hybrid(), qui n'est qu'un classement
	relatif entre les candidats d'UNE requete (verifie empiriquement : une
	question totalement hors-corpus obtenait quand meme un score RRF eleve,
	proche de celui d'une vraie correspondance, parce que RRF n'a aucune notion
	d'"aucun document pertinent" -- il classe toujours le meilleur candidat
	disponible, pertinent ou non)."""
	settings = get_settings()
	client = _get_client()
	query_vector = embed_query(question)
	query_filter = models.Filter(must=[models.FieldCondition(key="langue", match=models.MatchValue(value=language))])

	response = client.query_points(
		collection_name=settings.qdrant_collection_loi_by_article,
		query=query_vector,
		using="dense",
		query_filter=query_filter,
		limit=1,
		with_payload=False,
	)
	return float(response.points[0].score) if response.points else 0.0


@dataclass
class ArticleSearchResult:
	id_chunk: str
	source_file: str
	numero_article: int | None
	langue: str
	texte: str
	score: float
	statut: str = "en_vigueur"
	category: str = "non_classe"


def search_by_article_hybrid(question: str, language: str = "fr", top_k: int = 5) -> list[ArticleSearchResult]:
	"""Recherche hybride dense (E5) + lexical (BM25 natif) sur la collection
	separee, fusion RRF -- verifie en conditions reelles sur Qdrant 1.20."""
	settings = get_settings()
	client = _get_client()
	query_vector = embed_query(question)

	query_filter = models.Filter(must=[models.FieldCondition(key="langue", match=models.MatchValue(value=language))])
	candidate_limit = max(top_k * 3, top_k)

	response = client.query_points(
		collection_name=settings.qdrant_collection_loi_by_article,
		prefetch=[
			models.Prefetch(query=query_vector, using="dense", filter=query_filter, limit=candidate_limit),
			models.Prefetch(query=models.TextQuery(text=question), using="texte", filter=query_filter, limit=candidate_limit),
		],
		query=models.FusionQuery(fusion=models.Fusion.RRF),
		limit=top_k,
		with_payload=True,
	)

	return [
		ArticleSearchResult(
			id_chunk=point.payload.get("id_chunk", "unknown"),
			source_file=point.payload.get("source_file", ""),
			numero_article=point.payload.get("numero_article"),
			langue=point.payload.get("langue", language),
			texte=point.payload.get("texte", ""),
			score=float(point.score),
			# .get() avec defaut : les points indexes avant cet ajout n'ont pas ces
			# champs dans leur payload, on ne veut pas planter dessus.
			statut=point.payload.get("statut", "en_vigueur"),
			category=point.payload.get("category", "non_classe"),
		)
		for point in response.points
	]
