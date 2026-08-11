from __future__ import annotations

from backend.app.core.config import Settings
from backend.app.llm.interfaces import BaseLLMClient


class GeminiLLMClient(BaseLLMClient):
	def __init__(self, settings: Settings) -> None:
		super().__init__(settings)
		if not settings.gemini_api_key:
			raise RuntimeError("GEMINI_API_KEY is required when llm_provider=gemini")

		try:
			import google.generativeai as genai
		except Exception as exc:  # pragma: no cover
			raise RuntimeError("google-generativeai package is required for Gemini LLM") from exc

		genai.configure(api_key=settings.gemini_api_key)
		self._model = genai.GenerativeModel(model_name=settings.gemini_llm_model)

	def generate(self, prompt: str, system_prompt: str | None = None) -> str:
		full_prompt = prompt if not system_prompt else f"{system_prompt}\n\n{prompt}"
		response = self._model.generate_content(full_prompt)
		text = getattr(response, "text", "") or ""
		return text.strip()
