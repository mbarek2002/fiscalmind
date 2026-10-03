from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.app.core.config import Settings


class BaseLLMClient(ABC):
	def __init__(self, settings: Settings) -> None:
		self.settings = settings

	@abstractmethod
	def generate(self, prompt: str, system_prompt: str | None = None) -> str:
		raise NotImplementedError


@dataclass
class EmbeddingResult:
	dense: list[float]
	# token_id -> weight. None for providers with no native sparse output (OpenAI/Gemini) —
	# those fall back to dense-only search rather than a fake/placeholder sparse vector.
	sparse: dict[int, float] | None = None


class BaseEmbeddingClient(ABC):
	def __init__(self, settings: Settings) -> None:
		self.settings = settings

	@abstractmethod
	def embed_text(self, text: str) -> list[float]:
		raise NotImplementedError

	def embed_texts(self, texts: list[str]) -> list[list[float]]:
		return [self.embed_text(item) for item in texts]

	def embed_hybrid(self, text: str) -> EmbeddingResult:
		"""Dense + sparse in one call where the provider supports it natively (BGE-M3 locally).
		Default implementation falls back to dense-only for providers without sparse output."""
		return EmbeddingResult(dense=self.embed_text(text), sparse=None)
