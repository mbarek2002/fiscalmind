from __future__ import annotations

from functools import lru_cache

from backend.app.core.config import Settings, get_settings
from backend.app.retrieval.hybrid_search import RetrievedChunk


@lru_cache
def _get_local_cross_encoder(model_name: str):
	try:
		from sentence_transformers import CrossEncoder
	except Exception as exc:  # pragma: no cover - depends on optional runtime libs
		raise RuntimeError(
			"sentence-transformers is required for local reranking. Install dependencies from requirements.txt"
		) from exc

	return CrossEncoder(model_name)


def _score_with_local_cross_encoder(
	question: str,
	chunks: list[RetrievedChunk],
	settings: Settings,
) -> list[float]:
	model = _get_local_cross_encoder(settings.local_reranker_model_name)
	pairs = [[question, chunk.extrait] for chunk in chunks]
	raw_scores = model.predict(pairs)
	return [float(score) for score in raw_scores]


def _score_with_remote_provider(
	question: str,
	chunks: list[RetrievedChunk],
	settings: Settings,
) -> list[float]:
	provider = settings.reranker_provider
	raise RuntimeError(
		f"Reranker provider '{provider}' is not implemented yet. "
		"Use reranker_provider=local for now."
	)


def rerank_chunks(question: str, chunks: list[RetrievedChunk], top_k: int | None = None) -> list[RetrievedChunk]:
	if not chunks:
		return []

	settings = get_settings()
	limit = len(chunks) if top_k is None else max(1, min(top_k, len(chunks)))

	try:
		if settings.reranker_provider == "local":
			scores = _score_with_local_cross_encoder(question=question, chunks=chunks, settings=settings)
		else:
			scores = _score_with_remote_provider(question=question, chunks=chunks, settings=settings)
	except Exception as exc:
		if settings.provider_strict_mode_enabled:
			raise RuntimeError(
				"Reranker is unavailable while strict provider mode is enabled"
			) from exc
		# Non-strict mode keeps hybrid ranking order.
		return sorted(chunks, key=lambda item: item.fused_score, reverse=True)[:limit]

	for chunk, score in zip(chunks, scores, strict=False):
		chunk.fused_score = score

	chunks.sort(key=lambda item: item.fused_score, reverse=True)
	return chunks[:limit]
