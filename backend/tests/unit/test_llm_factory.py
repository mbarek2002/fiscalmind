from __future__ import annotations

import pytest

from backend.app.core.config import Settings
from backend.app.llm.factory import EmbeddingClientFactory, LLMClientFactory


class _DummyEmbeddingClient:
	def __init__(self, settings: Settings) -> None:
		self.settings = settings


class _DummyLLMClient:
	def __init__(self, settings: Settings) -> None:
		self.settings = settings


def _settings(**overrides: object) -> Settings:
	base = {
		"database_url": "sqlite+aiosqlite:///./test_factory.db",
		"embedding_provider": "local",
		"llm_provider": "local",
	}
	base.update(overrides)
	return Settings(**base)


def test_embedding_factory_selects_local(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.llm import factory as factory_mod

	monkeypatch.setattr(factory_mod, "LocalEmbeddingClient", _DummyEmbeddingClient)
	settings = _settings(embedding_provider="local")

	client = EmbeddingClientFactory.create(settings)

	assert isinstance(client, _DummyEmbeddingClient)


def test_embedding_factory_selects_openai(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.llm import factory as factory_mod

	monkeypatch.setattr(factory_mod, "OpenAIEmbeddingClient", _DummyEmbeddingClient)
	settings = _settings(embedding_provider="openai")

	client = EmbeddingClientFactory.create(settings)

	assert isinstance(client, _DummyEmbeddingClient)


def test_embedding_factory_selects_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.llm import factory as factory_mod

	monkeypatch.setattr(factory_mod, "GeminiEmbeddingClient", _DummyEmbeddingClient)
	settings = _settings(embedding_provider="gemini")

	client = EmbeddingClientFactory.create(settings)

	assert isinstance(client, _DummyEmbeddingClient)


def test_llm_factory_selects_local(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.llm import factory as factory_mod

	monkeypatch.setattr(factory_mod, "LocalVLLMClient", _DummyLLMClient)
	settings = _settings(llm_provider="local")

	client = LLMClientFactory.create(settings)

	assert isinstance(client, _DummyLLMClient)


def test_llm_factory_selects_openai(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.llm import factory as factory_mod

	monkeypatch.setattr(factory_mod, "OpenAILLMClient", _DummyLLMClient)
	settings = _settings(llm_provider="openai")

	client = LLMClientFactory.create(settings)

	assert isinstance(client, _DummyLLMClient)


def test_llm_factory_selects_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.llm import factory as factory_mod

	monkeypatch.setattr(factory_mod, "GeminiLLMClient", _DummyLLMClient)
	settings = _settings(llm_provider="gemini")

	client = LLMClientFactory.create(settings)

	assert isinstance(client, _DummyLLMClient)


def test_llm_factory_selects_nvidia(monkeypatch: pytest.MonkeyPatch) -> None:
	from backend.app.llm import factory as factory_mod

	monkeypatch.setattr(factory_mod, "NvidiaLLMClient", _DummyLLMClient)
	settings = _settings(llm_provider="nvidia")

	client = LLMClientFactory.create(settings)

	assert isinstance(client, _DummyLLMClient)


def test_nvidia_client_requires_api_key() -> None:
	from backend.app.llm.providers.generation.nvidia_llm import NvidiaLLMClient

	with pytest.raises(RuntimeError, match="NVIDIA_API_KEY"):
		NvidiaLLMClient(_settings(llm_provider="nvidia", nvidia_api_key=None))


def test_nvidia_client_sends_thinking_flag(monkeypatch: pytest.MonkeyPatch) -> None:
	import openai

	captured: dict = {}

	class _FakeOpenAI:
		def __init__(self, api_key: str, base_url: str | None) -> None:
			captured["base_url"] = base_url
			self.chat = self
			self.completions = self

		def create(self, **kwargs: object) -> object:
			captured.update(kwargs)
			message = type("M", (), {"content": " ok "})()
			choice = type("C", (), {"message": message})()
			return type("R", (), {"choices": [choice]})()

	monkeypatch.setattr(openai, "OpenAI", _FakeOpenAI)
	from backend.app.llm.providers.generation.nvidia_llm import NvidiaLLMClient

	client = NvidiaLLMClient(_settings(llm_provider="nvidia", nvidia_api_key="nvapi-test"))

	assert client.generate("question") == "ok"
	assert captured["base_url"] == "https://integrate.api.nvidia.com/v1"
	assert captured["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}


def test_settings_rejects_invalid_embedding_provider() -> None:
	with pytest.raises(ValueError, match="embedding_provider must be one of"):
		_settings(embedding_provider="cohere")


def test_settings_rejects_invalid_llm_provider() -> None:
	with pytest.raises(ValueError, match="llm_provider must be one of"):
		_settings(llm_provider="anthropic")
