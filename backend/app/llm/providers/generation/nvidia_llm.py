from __future__ import annotations

from backend.app.core.config import Settings
from backend.app.llm.providers.generation.openai_compatible import OpenAICompatibleChatClient


class NvidiaLLMClient(OpenAICompatibleChatClient):
	"""API NVIDIA (build.nvidia.com / NIM), compatible avec le format OpenAI."""

	def __init__(self, settings: Settings) -> None:
		if not settings.nvidia_api_key:
			raise RuntimeError("NVIDIA_API_KEY is required when llm_provider=nvidia")
		super().__init__(
			settings=settings,
			model=settings.nvidia_llm_model,
			base_url=settings.nvidia_base_url,
			api_key=settings.nvidia_api_key,
			# Mode "reflexion" (Nemotron) : plus lent, desactive par defaut.
			extra_body={"chat_template_kwargs": {"enable_thinking": settings.nvidia_enable_thinking}},
		)
