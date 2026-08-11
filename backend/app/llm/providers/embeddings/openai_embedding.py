from __future__ import annotations

from backend.app.core.config import Settings
from backend.app.llm.interfaces import BaseEmbeddingClient
from backend.app.llm.utils import normalize_vector_size


class OpenAIEmbeddingClient(BaseEmbeddingClient):
	def __init__(self, settings: Settings) -> None:
		super().__init__(settings)
		if not settings.openai_api_key:
			raise RuntimeError("OPENAI_API_KEY is required when embedding_provider=openai")

		try:
			from openai import OpenAI
		except Exception as exc:  # pragma: no cover
			raise RuntimeError("openai package is required for OpenAI embeddings") from exc

		self._client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

	def embed_text(self, text: str) -> list[float]:
		response = self._client.embeddings.create(
			model=self.settings.openai_embedding_model,
			input=text or "",
		)
		vector = response.data[0].embedding
		return normalize_vector_size([float(v) for v in vector], self.settings.qdrant_vector_size)
