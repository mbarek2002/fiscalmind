from __future__ import annotations

from backend.app.core.config import get_settings
from backend.app.llm.factory import get_embedding_client
from backend.app.llm.interfaces import EmbeddingResult
from backend.app.retrieval.hybrid_search import deterministic_embedding

try:
	from qdrant_client import QdrantClient
except Exception:  # pragma: no cover - optional dependency in some environments
	QdrantClient = None


def _search_collection_hybrid(
	*,
	collection_name: str,
	question: str,
	language: str,
	top_k: int,
	row_builder,
) -> list[dict]:
	settings = get_settings()
	if not settings.qdrant_url:
		return []

	if QdrantClient is None:
		return []

	try:
		from qdrant_client.models import Filter, FieldCondition, MatchValue, Prefetch, FusionQuery, Fusion, SparseVector
	except Exception:
		return []

	try:
		client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
		query_filter = Filter(
			must=[
				FieldCondition(key="langue", match=MatchValue(value=language)),
			]
		)

		try:
			embedding = get_embedding_client().embed_hybrid(question)
		except Exception as exc:
			if settings.provider_strict_mode_enabled:
				raise RuntimeError(
					"Embedding provider is unavailable while strict provider mode is enabled"
				) from exc
			# Fallback keeps MVP functional even when external provider is unavailable.
			embedding = EmbeddingResult(dense=deterministic_embedding(question, settings.qdrant_vector_size), sparse=None)

		candidate_limit = max(top_k * 3, top_k)
		prefetch = [
			Prefetch(query=embedding.dense, using="dense", filter=query_filter, limit=candidate_limit),
		]
		if embedding.sparse:
			sparse_query = SparseVector(
				indices=list(embedding.sparse.keys()),
				values=list(embedding.sparse.values()),
			)
			prefetch.append(Prefetch(query=sparse_query, using="sparse", filter=query_filter, limit=candidate_limit))

		# With a single prefetch branch (no sparse vector available) there is nothing to fuse,
		# so query the dense branch directly instead of asking Qdrant to fuse one list with itself.
		if len(prefetch) == 1:
			response = client.query_points(
				collection_name=collection_name,
				query=embedding.dense,
				using="dense",
				query_filter=query_filter,
				limit=top_k,
				with_payload=True,
			)
		else:
			response = client.query_points(
				collection_name=collection_name,
				prefetch=prefetch,
				query=FusionQuery(fusion=Fusion.RRF),
				limit=top_k,
				with_payload=True,
			)

		results: list[dict] = []
		for point in response.points:
			payload = point.payload or {}
			extrait = payload.get("texte", "")
			score = float(point.score)
			results.append(row_builder(payload, extrait, score, score, score, language))
		return results
	except Exception as exc:
		if settings.provider_strict_mode_enabled:
			raise RuntimeError(
				f"Qdrant hybrid search on '{collection_name}' failed while strict provider mode is enabled"
			) from exc
		return []


def _legal_row(payload: dict, extrait: str, vec_score: float, lex_score: float, fused: float, language: str) -> dict:
	return {
		"article_id": payload.get("id_chunk", "unknown"),
		"loi": payload.get("loi", "Loi de Finance"),
		"numero_article": payload.get("numero_article", 0),
		"statut": payload.get("statut", "en_vigueur"),
		"langue": payload.get("langue", language),
		"extrait": extrait,
		"category": (payload.get("categorie_infraction") or ["non_classe"])[0],
		"dense_score": vec_score,
		"sparse_score": lex_score,
		"fused_score": fused,
	}


def _jurisprudence_row(payload: dict, extrait: str, vec_score: float, lex_score: float, fused: float, language: str) -> dict:
	return {
		"case_id": payload.get("id_chunk", "unknown"),
		"reference": payload.get("reference", payload.get("loi", "Affaire")),
		"resume": extrait,
		"langue": payload.get("langue", language),
		"categorie": (payload.get("categorie_infraction") or ["non_classe"])[0],
		"dense_score": vec_score,
		"sparse_score": lex_score,
		"fused_score": fused,
	}


def search_qdrant_hybrid(question: str, language: str = "fr", top_k: int = 3) -> list[dict]:
	settings = get_settings()
	return _search_collection_hybrid(
		collection_name=settings.qdrant_collection_loi,
		question=question,
		language=language,
		top_k=top_k,
		row_builder=_legal_row,
	)


def search_qdrant_jurisprudence_hybrid(question: str, language: str = "fr", top_k: int = 2) -> list[dict]:
	settings = get_settings()
	return _search_collection_hybrid(
		collection_name=settings.qdrant_collection_jurisprudence,
		question=question,
		language=language,
		top_k=top_k,
		row_builder=_jurisprudence_row,
	)
