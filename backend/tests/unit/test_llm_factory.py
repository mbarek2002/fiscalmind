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


def test_settings_rejects_invalid_embedding_provider() -> None:
	with pytest.raises(ValueError, match="embedding_provider must be one of"):
		_settings(embedding_provider="cohere")


def test_settings_rejects_invalid_llm_provider() -> None:
	with pytest.raises(ValueError, match="llm_provider must be one of"):
		_settings(llm_provider="anthropic")
