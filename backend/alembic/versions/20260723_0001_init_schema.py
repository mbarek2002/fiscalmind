"""init schema

Revision ID: 20260723_0001
Revises:
Create Date: 2026-07-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260723_0001"
down_revision = None
branch_labels = None
depends_on = None


user_role_enum = sa.Enum("citoyen", "avocat", "juge", "admin", name="userrole")
source_type_enum = sa.Enum("loi", "jurisprudence", name="documentsourcetype")
document_status_enum = sa.Enum("en_vigueur", "modifie", "abroge", name="documentstatus")

user_role_enum_no_create = postgresql.ENUM(
    "citoyen", "avocat", "juge", "admin", name="userrole", create_type=False
)
source_type_enum_no_create = postgresql.ENUM(
    "loi", "jurisprudence", name="documentsourcetype", create_type=False
)
document_status_enum_no_create = postgresql.ENUM(
    "en_vigueur", "modifie", "abroge", name="documentstatus", create_type=False
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
                CREATE TYPE userrole AS ENUM ('citoyen', 'avocat', 'juge', 'admin');
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'documentsourcetype') THEN
                CREATE TYPE documentsourcetype AS ENUM ('loi', 'jurisprudence');
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'documentstatus') THEN
                CREATE TYPE documentstatus AS ENUM ('en_vigueur', 'modifie', 'abroge');
            END IF;
        END
        $$;
        """
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum_no_create, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("preferred_lang", sa.String(length=5), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    op.create_table(
        "documents_metadata",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_type", source_type_enum_no_create, nullable=False),
        sa.Column("titre", sa.String(length=500), nullable=False),
        sa.Column("annee_loi", sa.Integer(), nullable=True),
        sa.Column("numero_article", sa.Integer(), nullable=True),
        sa.Column("langue", sa.String(length=5), nullable=False),
        sa.Column("id_article_lie", sa.String(length=36), nullable=True),
        sa.Column("statut", document_status_enum_no_create, nullable=False),
        sa.Column("date_entree_vigueur", sa.Date(), nullable=True),
        sa.Column("date_abrogation", sa.Date(), nullable=True),
        sa.Column("categorie_infraction", sa.JSON(), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column("anonymized", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_metadata_annee_loi"), "documents_metadata", ["annee_loi"], unique=False)
    op.create_index(op.f("ix_documents_metadata_source_type"), "documents_metadata", ["source_type"], unique=False)

    op.create_table(
        "query_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("final_answer", sa.Text(), nullable=False),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_query_logs_created_at"), "query_logs", ["created_at"], unique=False)

    op.create_table(
        "query_citations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("query_log_id", sa.String(length=36), nullable=False),
        sa.Column("article_id", sa.String(length=100), nullable=False),
        sa.Column("loi", sa.String(length=255), nullable=False),
        sa.Column("numero_article", sa.Integer(), nullable=False),
        sa.Column("statut", sa.String(length=50), nullable=False),
        sa.Column("langue", sa.String(length=5), nullable=False),
        sa.Column("extrait", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["query_log_id"], ["query_logs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("user_role", sa.String(length=20), nullable=False),
        sa.Column("query_id", sa.String(length=36), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("final_answer", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_query_id"), "audit_logs", ["query_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_query_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_table("query_citations")

    op.drop_index(op.f("ix_query_logs_created_at"), table_name="query_logs")
    op.drop_table("query_logs")

    op.drop_index(op.f("ix_documents_metadata_source_type"), table_name="documents_metadata")
    op.drop_index(op.f("ix_documents_metadata_annee_loi"), table_name="documents_metadata")
    op.drop_table("documents_metadata")

    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS documentstatus")
    op.execute("DROP TYPE IF EXISTS documentsourcetype")
    op.execute("DROP TYPE IF EXISTS userrole")
