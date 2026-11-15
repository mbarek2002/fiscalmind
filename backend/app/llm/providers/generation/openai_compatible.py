from __future__ import annotations

from backend.app.core.config import Settings
from backend.app.llm.interfaces import BaseLLMClient


class OpenAICompatibleChatClient(BaseLLMClient):
	def __init__(
		self,
		settings: Settings,
		model: str,
		base_url: str | None,
		api_key: str,
		extra_body: dict | None = None,
	) -> None:
		super().__init__(settings)
		# Parametres propres a un fournisseur (ex. NVIDIA chat_template_kwargs) ;
		# None = requete OpenAI standard, comportement inchange pour les autres.
		self._extra_body = extra_body
		try:
			from openai import OpenAI
		except Exception as exc:  # pragma: no cover - optional runtime dependency
			raise RuntimeError("openai package is required for OpenAI-compatible LLM clients") from exc

		self._client = OpenAI(api_key=api_key, base_url=base_url)
		self._model = model

	def generate(self, prompt: str, system_prompt: str | None = None) -> str:
		messages: list[dict[str, str]] = []
		if system_prompt:
			messages.append({"role": "system", "content": system_prompt})
		messages.append({"role": "user", "content": prompt})

		kwargs = {}
		if self._extra_body:
			kwargs["extra_body"] = self._extra_body
		response = self._client.chat.completions.create(
			model=self._model,
			messages=messages,
			temperature=self.settings.llm_temperature,
			max_tokens=self.settings.llm_max_tokens,
			**kwargs,
		)
		content = response.choices[0].message.content if response.choices else ""
		return (content or "").strip()
