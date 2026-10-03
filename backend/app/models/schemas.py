from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from backend.app.models.enums import (
	CitationType,
	FinancialDocumentStatus,
	FinancialSourceType,
	FinancialSubmissionStatus,
	IngestionStatus,
	UserRole,
)


class QueryRequest(BaseModel):
	question: str = Field(min_length=3, max_length=4000)
	language: str = Field(default="fr", pattern="^(fr|ar)$")


class CitationSchema(BaseModel):
	article_id: str
	loi: str
	numero_article: int
	statut: str
	langue: str
	extrait: str


class JurisprudenceCitationSchema(BaseModel):
	case_id: str
	reference: str
	resume: str


class QueryResponse(BaseModel):
	query_id: str
	final_answer: str
	verification_status: str
	citations: list[CitationSchema]
	jurisprudence: list[JurisprudenceCitationSchema] = []
	disclaimer: str
	question: str | None = None
	created_at: datetime | None = None


class UserCreateRequest(BaseModel):
	email: EmailStr
	password: str = Field(min_length=8, max_length=128)
	full_name: str = Field(min_length=2, max_length=255)
	role: UserRole = UserRole.citoyen
	preferred_lang: str = Field(default="fr", pattern="^(fr|ar)$")


class UserPublic(BaseModel):
	id: str
	email: EmailStr
	full_name: str
	role: UserRole
	is_active: bool
	preferred_lang: str
	created_at: datetime


class LoginRequest(BaseModel):
	email: EmailStr
	password: str = Field(min_length=8, max_length=128)


class TokenPairResponse(BaseModel):
	access_token: str
	refresh_token: str
	token_type: str = "bearer"
	user: UserPublic


class RefreshRequest(BaseModel):
	refresh_token: str


class UpdateProfileRequest(BaseModel):
	full_name: str | None = Field(default=None, min_length=2, max_length=255)
	preferred_lang: str | None = Field(default=None, pattern="^(fr|ar)$")


class DocumentPublic(BaseModel):
	id: str
	filename: str
	size_bytes: int
	status: IngestionStatus
	chunks: int
	uploaded_at: datetime
	error: str | None = None


class CompanyCreateRequest(BaseModel):
	name: str = Field(min_length=2, max_length=255)
	matricule_fiscal: str = Field(min_length=3, max_length=50)
	secteur_activite: str | None = Field(default=None, max_length=255)


class CompanyPublic(BaseModel):
	id: str
	name: str
	matricule_fiscal: str
	secteur_activite: str | None = None
	created_at: datetime


class FinancialSubmissionCreateRequest(BaseModel):
	source_type: FinancialSourceType
	free_text: str | None = Field(default=None, max_length=8000)
	structured_data: dict | None = None


class FinancialDocumentPublic(BaseModel):
	id: str
	filename: str
	size_bytes: int
	status: FinancialDocumentStatus
	uploaded_at: datetime
	error: str | None = None


class InfractionCitationPublic(BaseModel):
	id: str
	citation_type: CitationType
	ref_id: str
	loi: str | None = None
	numero_article: int | None = None
	reference: str | None = None
	statut: str | None = None
	langue: str | None = None
	extrait: str


class InfractionFindingPublic(BaseModel):
	id: str
	categorie_infraction: str
	description: str
	severite: str | None = None
	confidence_score: float | None = None
	citations: list[InfractionCitationPublic] = []
	created_at: datetime


class ChunkDebugInfo(BaseModel):
	chunk_id: str
	chunk_index: int
	text: str
	langue: str
	numero_article: int | None
	headers: dict[str, str]
	char_count: int


class ExtractChunkDebugResponse(BaseModel):
	filename: str
	mode_requested: str
	page_count: int
	extraction_warnings: list[str]
	text_length: int
	chunk_count: int
	chunks: list[ChunkDebugInfo]


class RetrieveDebugRequest(BaseModel):
	question: str = Field(min_length=3, max_length=4000)
	language: str = Field(default="fr", pattern="^(fr|ar)$")
	top_k: int = Field(default=3, ge=1, le=20)
	include_jurisprudence: bool = True


class RetrievedArticleDebugInfo(BaseModel):
	article_id: str
	loi: str
	numero_article: int
	statut: str
	langue: str
	extrait: str
	category: str
	dense_score: float
	sparse_score: float
	fused_score: float


class RetrievedJurisprudenceDebugInfo(BaseModel):
	case_id: str
	reference: str
	resume: str
	langue: str
	categorie: str
	dense_score: float
	sparse_score: float
	fused_score: float


class RetrieveDebugResponse(BaseModel):
	question: str
	language: str
	legal_results: list[RetrievedArticleDebugInfo]
	jurisprudence_results: list[RetrievedJurisprudenceDebugInfo]
	graph_context_ids: list[str]


class FinancialSubmissionPublic(BaseModel):
	id: str
	company_id: str
	source_type: FinancialSourceType
	status: FinancialSubmissionStatus
	free_text: str | None = None
	structured_data: dict | None = None
	final_summary: str | None = None
	verification_status: str | None = None
	disclaimer: str | None = None
	documents: list[FinancialDocumentPublic] = []
	findings: list[InfractionFindingPublic] = []
	created_at: datetime
