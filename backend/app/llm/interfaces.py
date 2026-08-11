from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.core.config import Settings


class BaseLLMClient(ABC):
	def __init__(self, settings: Settings) -> None:
		self.settings = settings

	@abstractmethod
	def generate(self, prompt: str, system_prompt: str | None = None) -> str:
		raise NotImplementedError


class BaseEmbeddingClient(ABC):
	def __init__(self, settings: Settings) -> None:
		self.settings = settings

	@abstractmethod
	def embed_text(self, text: str) -> list[float]:
		raise NotImplementedError

	def embed_texts(self, texts: list[str]) -> list[list[float]]:
		return [self.embed_text(item) for item in texts]
