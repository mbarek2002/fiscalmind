from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from backend.app.models.enums import UserRole


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


class QueryResponse(BaseModel):
	query_id: str
	final_answer: str
	verification_status: str
	citations: list[CitationSchema]
	disclaimer: str


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
