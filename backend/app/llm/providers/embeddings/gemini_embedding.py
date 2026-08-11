from __future__ import annotations

from backend.app.core.config import Settings
from backend.app.llm.interfaces import BaseEmbeddingClient
from backend.app.llm.utils import normalize_vector_size


class GeminiEmbeddingClient(BaseEmbeddingClient):
	def __init__(self, settings: Settings) -> None:
		super().__init__(settings)
		if not settings.gemini_api_key:
			raise RuntimeError("GEMINI_API_KEY is required when embedding_provider=gemini")

		try:
			import google.generativeai as genai
		except Exception as exc:  # pragma: no cover
			raise RuntimeError("google-generativeai package is required for Gemini embeddings") from exc

		genai.configure(api_key=settings.gemini_api_key)
		self._genai = genai

	def embed_text(self, text: str) -> list[float]:
		response = self._genai.embed_content(
			model=self.settings.gemini_embedding_model,
			content=text or "",
			task_type="retrieval_query",
		)
		vector = response["embedding"]
		return normalize_vector_size([float(v) for v in vector], self.settings.qdrant_vector_size)
