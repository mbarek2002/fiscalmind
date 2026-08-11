from __future__ import annotations

from backend.app.core.config import Settings
from backend.app.llm.providers.generation.openai_compatible import OpenAICompatibleChatClient


class OpenAILLMClient(OpenAICompatibleChatClient):
	def __init__(self, settings: Settings) -> None:
		if not settings.openai_api_key:
			raise RuntimeError("OPENAI_API_KEY is required when llm_provider=openai")
		super().__init__(
			settings=settings,
			model=settings.openai_llm_model,
			base_url=settings.openai_base_url,
			api_key=settings.openai_api_key,
		)
