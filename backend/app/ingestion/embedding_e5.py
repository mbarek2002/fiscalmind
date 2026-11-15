from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from backend.app.core.config import get_settings


@lru_cache
def _get_e5_model() -> SentenceTransformer:
	settings = get_settings()
	return SentenceTransformer(settings.e5_embedding_model_name)


def embed_passages(texts: list[str]) -> list[list[float]]:
	"""Embed des documents (articles de loi) -- prefixe 'passage: ' requis par E5."""
	model = _get_e5_model()
	prefixed = [f"passage: {text}" for text in texts]
	return model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False).tolist()


def embed_query(text: str) -> list[float]:
	"""Embed une question utilisateur -- prefixe 'query: ' requis par E5."""
	model = _get_e5_model()
	return model.encode(f"query: {text}", normalize_embeddings=True).tolist()
