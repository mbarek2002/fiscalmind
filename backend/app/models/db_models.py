from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base
from backend.app.models.enums import (
	CitationType,
	DocumentSourceType,
	DocumentStatus,
	FinancialDocumentStatus,
	FinancialSourceType,
	FinancialSubmissionStatus,
	IngestionStatus,
	UserRole,
)


class TimestampMixin:
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		default=lambda: datetime.now(UTC),
		onupdate=lambda: datetime.now(UTC),
	)


class User(Base, TimestampMixin):
	__tablename__ = "users"

	id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
	email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
	hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
	full_name: Mapped[str] = mapped_column(String(255), nullable=False)
	role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.citoyen, nullable=False, index=True)
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	preferred_lang: Mapped[str] = mapped_column(String(5), default="fr", nullable=False)
	company_id: Mapped[str | None] = mapped_column(
		String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
	)

	query_logs: Mapped[list["QueryLog"]] = relationship(back_populates="user")
	audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
	company: Mapped["Company | None"] = relationship(back_populates="users", foreign_keys=[company_id])


class Company(Base, TimestampMixin):
	__tablename__ = "companies"

	id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
	name: Mapped[str] = mapped_column(String(255), nullable=False)
	matricule_fiscal: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
	secteur_activite: Mapped[str | None] = mapped_column(String(255), nullable=True)
	created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

	users: Mapped[list["User"]] = relationship(back_populates="company", foreign_keys=[User.company_id])
	submissions: Mapped[list["FinancialSubmission"]] = relationship(
		back_populates="company", cascade="all, delete-orphan"
	)


class FinancialSubmission(Base, TimestampMixin):
	__tablename__ = "financial_submissions"

	id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
	company_id: Mapped[str] = mapped_column(
		String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
	)
	submitted_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
	source_type: Mapped[FinancialSourceType] = mapped_column(Enum(FinancialSourceType), nullable=False)
	free_text: Mapped[str | None] = mapped_column(Text, nullable=True)
	structured_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	status: Mapped[FinancialSubmissionStatus] = mapped_column(
		Enum(FinancialSubmissionStatus), default=FinancialSubmissionStatus.pending, nullable=False, index=True
	)
	final_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
	verification_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
	disclaimer: Mapped[str | None] = mapped_column(Text, nullable=True)

	company: Mapped["Company"] = relationship(back_populates="submissions")
	documents: Mapped[list["FinancialDocument"]] = relationship(
		back_populates="submission", cascade="all, delete-orphan"
	)
	findings: Mapped[list["InfractionFinding"]] = relationship(
		back_populates="submission", cascade="all, delete-orphan"
	)


class FinancialDocument(Base, TimestampMixin):
	__tablename__ = "financial_documents"

	id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
	submission_id: Mapped[str] = mapped_column(
		String(36), ForeignKey("financial_submissions.id", ondelete="CASCADE"), nullable=False, index=True
	)
	original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
	storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
	mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
	size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	extraction_status: Mapped[FinancialDocumentStatus] = mapped_column(
		Enum(FinancialDocumentStatus), default=FinancialDocumentStatus.uploaded, nullable=False
	)
	extracted_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)

	submission: Mapped["FinancialSubmission"] = relationship(back_populates="documents")


class InfractionFinding(Base):
	__tablename__ = "infraction_findings"

	id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
	submission_id: Mapped[str] = mapped_column(
		String(36), ForeignKey("financial_submissions.id", ondelete="CASCADE"), nullable=False, index=True
	)
	categorie_infraction: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
	description: Mapped[str] = mapped_column(Text, nullable=False)
	severite: Mapped[str | None] = mapped_column(String(20), nullable=True)
	confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

	submission: Mapped["FinancialSubmission"] = relationship(back_populates="findings")
	citations: Mapped[list["InfractionCitation"]] = relationship(
		back_populates="finding", cascade="all, delete-orphan"
	)


class InfractionCitation(Base):
	__tablename__ = "infraction_citations"

	id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
	finding_id: Mapped[str] = mapped_column(
		String(36), ForeignKey("infraction_findings.id", ondelete="CASCADE"), nullable=False, index=True
	)
	citation_type: Mapped[CitationType] = mapped_column(Enum(CitationType), nullable=False)
	ref_id: Mapped[str] = mapped_column(String(100), nullable=False)
	loi: Mapped[str | None] = mapped_column(String(255), nullable=True)
	numero_article: Mapped[int | None] = mapped_column(Integer, nullable=True)
	reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
	statut: Mapped[str | None] = mapped_column(String(50), nullable=True)
	langue: Mapped[str | None] = mapped_column(String(5), nullable=True)
	extrait: Mapped[str] = mapped_column(Text, nullable=False)

	finding: Mapped["InfractionFinding"] = relationship(back_populates="citations")


class DocumentMetadata(Base, TimestampMixin):
	__tablename__ = "documents_metadata"

	id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
	source_type: Mapped[DocumentSourceType] = mapped_column(Enum(DocumentSourceType), nullable=False, index=True)
	titre: Mapped[str] = mapped_column(String(500), nullable=False)
	annee_loi: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
	numero_article: Mapped[int | None] = mapped_column(Integer, nullable=True)
	langue: Mapped[str] = mapped_column(String(5), nullable=False)
	id_article_lie: Mapped[str | None] = mapped_column(String(36), nullable=True)
	statut: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.en_vigueur, nullable=False)
	date_entree_vigueur: Mapped[date | None] = mapped_column(Date, nullable=True)
	date_abrogation: Mapped[date | None] = mapped_column(Date, nullable=True)
	categorie_infraction: Mapped[list[str]] = mapped_column(JSON, default=list)
	storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
	anonymized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
	size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	ingestion_status: Mapped[IngestionStatus] = mapped_column(
		Enum(IngestionStatus), default=IngestionStatus.uploaded, nullable=False, index=True
	)
	chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	ingestion_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class QueryLog(Base):
	__tablename__ = "query_logs"

	id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
	user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
	question: Mapped[str] = mapped_column(Text, nullable=False)
	final_answer: Mapped[str] = mapped_column(Text, nullable=False)
	verification_status: Mapped[str] = mapped_column(String(30), nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)

	user: Mapped[User] = relationship(back_populates="query_logs")
	citations: Mapped[list["QueryCitation"]] = relationship(back_populates="query_log", cascade="all, delete-orphan")


class QueryCitation(Base):
	__tablename__ = "query_citations"

	id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
	query_log_id: Mapped[str] = mapped_column(String(36), ForeignKey("query_logs.id", ondelete="CASCADE"), nullable=False)
	article_id: Mapped[str] = mapped_column(String(100), nullable=False)
	loi: Mapped[str] = mapped_column(String(255), nullable=False)
	numero_article: Mapped[int] = mapped_column(Integer, nullable=False)
	statut: Mapped[str] = mapped_column(String(50), nullable=False)
	langue: Mapped[str] = mapped_column(String(5), nullable=False)
	extrait: Mapped[str] = mapped_column(Text, nullable=False)

	query_log: Mapped[QueryLog] = relationship(back_populates="citations")


class RefreshToken(Base):
	__tablename__ = "refresh_tokens"

	id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
	user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
	expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AuditLog(Base):
	__tablename__ = "audit_logs"

	id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
	user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
	user_role: Mapped[str] = mapped_column(String(20), nullable=False)
	query_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
	question: Mapped[str] = mapped_column(Text, nullable=False)
	final_answer: Mapped[str] = mapped_column(Text, nullable=False)
	citations: Mapped[list[dict]] = mapped_column(JSON, default=list)
	verification_status: Mapped[str] = mapped_column(String(30), nullable=False)
	retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)

	user: Mapped[User] = relationship(back_populates="audit_logs")


@event.listens_for(AuditLog, "before_update", propagate=True)
def prevent_audit_update(mapper, connection, target) -> None:  # noqa: ANN001
	raise ValueError("Audit logs are immutable and cannot be updated.")


@event.listens_for(AuditLog, "before_delete", propagate=True)
def prevent_audit_delete(mapper, connection, target) -> None:  # noqa: ANN001
	raise ValueError("Audit logs are immutable and cannot be deleted.")
