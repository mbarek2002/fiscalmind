from __future__ import annotations

from functools import lru_cache

from backend.app.core.config import Settings, get_settings
from backend.app.llm.enums import Provider
from backend.app.llm.interfaces import BaseEmbeddingClient, BaseLLMClient
from backend.app.llm.providers.embeddings.gemini_embedding import GeminiEmbeddingClient
from backend.app.llm.providers.embeddings.local_embedding import LocalEmbeddingClient
from backend.app.llm.providers.embeddings.openai_embedding import OpenAIEmbeddingClient
from backend.app.llm.providers.generation.gemini_llm import GeminiLLMClient
from backend.app.llm.providers.generation.local_vllm import LocalVLLMClient
from backend.app.llm.providers.generation.openai_llm import OpenAILLMClient


class EmbeddingClientFactory:
	@staticmethod
	def create(settings: Settings) -> BaseEmbeddingClient:
		provider = Provider(settings.embedding_provider)
		if provider == Provider.local:
			return LocalEmbeddingClient(settings)
		if provider == Provider.openai:
			return OpenAIEmbeddingClient(settings)
		if provider == Provider.gemini:
			return GeminiEmbeddingClient(settings)
		raise ValueError(f"Unsupported embedding provider: {provider}")


class LLMClientFactory:
	@staticmethod
	def create(settings: Settings) -> BaseLLMClient:
		provider = Provider(settings.llm_provider)
		if provider == Provider.local:
			return LocalVLLMClient(settings)
		if provider == Provider.openai:
			return OpenAILLMClient(settings)
		if provider == Provider.gemini:
			return GeminiLLMClient(settings)
		raise ValueError(f"Unsupported llm provider: {provider}")


@lru_cache
def get_embedding_client() -> BaseEmbeddingClient:
	return EmbeddingClientFactory.create(get_settings())


@lru_cache
def get_llm_client() -> BaseLLMClient:
	return LLMClientFactory.create(get_settings())
