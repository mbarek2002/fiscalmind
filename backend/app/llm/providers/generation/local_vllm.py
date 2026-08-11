from __future__ import annotations

from backend.app.core.config import Settings
from backend.app.llm.providers.generation.openai_compatible import OpenAICompatibleChatClient


class LocalVLLMClient(OpenAICompatibleChatClient):
	def __init__(self, settings: Settings) -> None:
		super().__init__(
			settings=settings,
			model=settings.local_llm_model_name,
			base_url=settings.local_llm_base_url,
			api_key=settings.local_llm_api_key,
		)
