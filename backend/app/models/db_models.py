from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base
from backend.app.models.enums import DocumentSourceType, DocumentStatus, UserRole


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

	query_logs: Mapped[list["QueryLog"]] = relationship(back_populates="user")
	audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


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
