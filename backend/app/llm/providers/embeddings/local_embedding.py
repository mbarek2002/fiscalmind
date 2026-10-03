from __future__ import annotations

from backend.app.core.config import Settings
from backend.app.llm.interfaces import BaseEmbeddingClient, EmbeddingResult


class LocalEmbeddingClient(BaseEmbeddingClient):
	def __init__(self, settings: Settings) -> None:
		super().__init__(settings)
		try:
			from FlagEmbedding import BGEM3FlagModel
		except Exception as exc:  # pragma: no cover - optional runtime dependency
			raise RuntimeError(
				"FlagEmbedding is required for local BGE-M3 embeddings (dense+sparse). "
				"Install dependencies from requirements.txt"
			) from exc

		self._model = BGEM3FlagModel(settings.local_embedding_model_name, use_fp16=True)

	def embed_text(self, text: str) -> list[float]:
		return self.embed_hybrid(text).dense

	def embed_hybrid(self, text: str) -> EmbeddingResult:
		output = self._model.encode(
			[text or ""],
			return_dense=True,
			return_sparse=True,
			return_colbert_vecs=False,
		)
		dense = [float(v) for v in output["dense_vecs"][0]]
		# lexical_weights keys are token ids as strings (e.g. "24241"), values are np.float16 —
		# both need converting to plain Python types for Qdrant's SparseVector / JSON encoding.
		sparse = {int(token_id): float(weight) for token_id, weight in output["lexical_weights"][0].items()}
		return EmbeddingResult(dense=dense, sparse=sparse)
