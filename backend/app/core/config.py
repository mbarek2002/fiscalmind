from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=False,
		enable_decoding=False,
		extra="ignore",
	)

	app_name: str = "FiscalMind API"
	environment: str = "dev"

	secret_key: str = "change-me-in-production"
	jwt_algorithm: str = "HS256"
	access_token_expire_minutes: int = 30
	refresh_token_expire_minutes: int = 60 * 24 * 7

	database_url: str = "sqlite+aiosqlite:///./fiscalmind.db"
	cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"]

	qdrant_url: str | None = None
	qdrant_api_key: str | None = None
	qdrant_collection_loi: str = "loi_finance"
	qdrant_collection_jurisprudence: str = "jurisprudence"
	# BGE-M3's native dense output size — do not shrink this; it used to be artificially
	# truncated to 64, which silently destroyed embedding quality for every provider.
	qdrant_vector_size: int = 1024
	reranker_provider: str = "local"
	local_reranker_model_name: str = "BAAI/bge-reranker-v2-m3"
	reranker_candidate_multiplier: int = 3
	max_verification_retries: int = 2
	embedding_provider: str = "local"
	local_embedding_model_name: str = "BAAI/bge-m3"
	openai_embedding_model: str = "text-embedding-3-large"
	gemini_embedding_model: str = "models/text-embedding-004"
	neo4j_uri: str | None = None
	neo4j_username: str | None = None
	neo4j_password: str | None = None

	llm_provider: str = "local"
	llm_temperature: float = 0.2
	llm_max_tokens: int = 900
	strict_provider_mode: bool = False
	local_llm_model_name: str = "Qwen/Qwen2.5-14B-Instruct-AWQ"
	local_llm_base_url: str = "http://localhost:8000/v1"
	local_llm_api_key: str = "EMPTY"
	openai_api_key: str | None = None
	openai_base_url: str | None = None
	openai_llm_model: str = "gpt-4o-mini"
	gemini_api_key: str | None = None
	gemini_llm_model: str = "gemini-2.0-flash"

	minio_endpoint: str | None = None
	minio_access_key: str | None = None
	minio_secret_key: str | None = None
	minio_bucket_raw: str = "raw-documents"
	minio_secure: bool = False

	@field_validator("cors_origins", mode="before")
	@classmethod
	def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
		if isinstance(value, list):
			return value
		if not value:
			return []
		return [item.strip() for item in value.split(",") if item.strip()]

	@property
	def sync_database_url(self) -> str:
		return self.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")

	@property
	def provider_strict_mode_enabled(self) -> bool:
		env = (self.environment or "").strip().lower()
		return self.strict_provider_mode or env in {"prod", "production"}

	@field_validator("embedding_provider", mode="before")
	@classmethod
	def validate_embedding_provider(cls, value: str) -> str:
		provider = (value or "local").strip().lower()
		if provider not in {"local", "openai", "gemini"}:
			raise ValueError("embedding_provider must be one of: local, openai, gemini")
		return provider

	@field_validator("reranker_provider", mode="before")
	@classmethod
	def validate_reranker_provider(cls, value: str) -> str:
		provider = (value or "local").strip().lower()
		if provider not in {"local", "openai", "gemini"}:
			raise ValueError("reranker_provider must be one of: local, openai, gemini")
		return provider

	@field_validator("llm_provider", mode="before")
	@classmethod
	def validate_llm_provider(cls, value: str) -> str:
		provider = (value or "local").strip().lower()
		if provider not in {"local", "openai", "gemini"}:
			raise ValueError("llm_provider must be one of: local, openai, gemini")
		return provider


@lru_cache
def get_settings() -> Settings:
	return Settings()
