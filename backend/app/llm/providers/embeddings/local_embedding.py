from __future__ import annotations

from backend.app.core.config import Settings
from backend.app.llm.interfaces import BaseEmbeddingClient
from backend.app.llm.utils import normalize_vector_size


class LocalEmbeddingClient(BaseEmbeddingClient):
	def __init__(self, settings: Settings) -> None:
		super().__init__(settings)
		try:
			from sentence_transformers import SentenceTransformer
		except Exception as exc:  # pragma: no cover - optional runtime dependency
			raise RuntimeError(
				"sentence-transformers is required for local embeddings. Install dependencies from requirements.txt"
			) from exc

		self._model = SentenceTransformer(settings.local_embedding_model_name)

	def embed_text(self, text: str) -> list[float]:
		vector = self._model.encode(text or "", normalize_embeddings=True).tolist()
		return normalize_vector_size([float(v) for v in vector], self.settings.qdrant_vector_size)
