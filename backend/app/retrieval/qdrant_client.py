from __future__ import annotations

from backend.app.core.config import get_settings
from backend.app.llm.factory import get_embedding_client
from backend.app.retrieval.hybrid_search import deterministic_embedding, lexical_score

try:
	from qdrant_client import QdrantClient
except Exception:  # pragma: no cover - optional dependency in some environments
	QdrantClient = None


def search_qdrant_hybrid(question: str, language: str = "fr", top_k: int = 3) -> list[dict]:
	settings = get_settings()
	if not settings.qdrant_url:
		return []

	if QdrantClient is None:
		return []

	try:
		from qdrant_client.models import Filter, FieldCondition, MatchValue
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
			query_vector = get_embedding_client().embed_text(question)
		except Exception as exc:
			if settings.provider_strict_mode_enabled:
				raise RuntimeError(
					"Embedding provider is unavailable while strict provider mode is enabled"
				) from exc
			# Fallback keeps MVP functional even when external provider is unavailable.
			query_vector = deterministic_embedding(question, settings.qdrant_vector_size)
		points = client.search(
			collection_name=settings.qdrant_collection_loi,
			query_vector=query_vector,
			query_filter=query_filter,
			limit=max(top_k * 3, top_k),
		)

		results: list[dict] = []
		for point in points:
			payload = point.payload or {}
			extrait = payload.get("texte", "")
			lex_score = lexical_score(question, extrait)
			vec_score = float(point.score)
			fused = (0.7 * vec_score) + (0.3 * lex_score)
			results.append(
				{
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
			)

		results.sort(key=lambda row: row["fused_score"], reverse=True)
		return results[:top_k]
	except Exception as exc:
		if settings.provider_strict_mode_enabled:
			raise RuntimeError(
				"Qdrant hybrid search failed while strict provider mode is enabled"
			) from exc
		return []
