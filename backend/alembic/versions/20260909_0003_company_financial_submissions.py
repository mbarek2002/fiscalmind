"""company and financial submissions

Revision ID: 20260909_0003
Revises: 20260817_0002
Create Date: 2026-09-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260909_0003"
down_revision = "20260817_0002"
branch_labels = None
depends_on = None


financial_source_type_enum_no_create = postgresql.ENUM(
    "document", "formulaire", "texte_libre", "mixte", name="financialsourcetype", create_type=False
)
financial_submission_status_enum_no_create = postgresql.ENUM(
    "pending", "analyzing", "completed", "failed", name="financialsubmissionstatus", create_type=False
)
financial_document_status_enum_no_create = postgresql.ENUM(
    "uploaded", "processing", "extracted", "failed", name="financialdocumentstatus", create_type=False
)
citation_type_enum_no_create = postgresql.ENUM(
    "article", "jurisprudence", name="citationtype", create_type=False
)


def upgrade() -> None:
    # New value on the existing `userrole` enum for the primary actor of this use case
    # (a company account). Postgres allows ADD VALUE inside a transaction since v12.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'userrole' AND e.enumlabel = 'entreprise'
            ) THEN
                ALTER TYPE userrole ADD VALUE 'entreprise';
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'financialsourcetype') THEN
                CREATE TYPE financialsourcetype AS ENUM ('document', 'formulaire', 'texte_libre', 'mixte');
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'financialsubmissionstatus') THEN
                CREATE TYPE financialsubmissionstatus AS ENUM ('pending', 'analyzing', 'completed', 'failed');
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'financialdocumentstatus') THEN
                CREATE TYPE financialdocumentstatus AS ENUM ('uploaded', 'processing', 'extracted', 'failed');
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'citationtype') THEN
                CREATE TYPE citationtype AS ENUM ('article', 'jurisprudence');
            END IF;
        END
        $$;
        """
    )

    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("matricule_fiscal", sa.String(length=50), nullable=False),
        sa.Column("secteur_activite", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("matricule_fiscal"),
    )
    op.create_index(op.f("ix_companies_matricule_fiscal"), "companies", ["matricule_fiscal"], unique=True)

    op.add_column("users", sa.Column("company_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_users_company_id_companies", "users", "companies", ["company_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index(op.f("ix_users_company_id"), "users", ["company_id"], unique=False)

    op.create_table(
        "financial_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("submitted_by", sa.String(length=36), nullable=False),
        sa.Column("source_type", financial_source_type_enum_no_create, nullable=False),
        sa.Column("free_text", sa.Text(), nullable=True),
        sa.Column("structured_data", sa.JSON(), nullable=True),
        sa.Column("status", financial_submission_status_enum_no_create, nullable=False),
        sa.Column("final_summary", sa.Text(), nullable=True),
        sa.Column("verification_status", sa.String(length=30), nullable=True),
        sa.Column("disclaimer", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_financial_submissions_company_id"), "financial_submissions", ["company_id"], unique=False
    )
    op.create_index(op.f("ix_financial_submissions_status"), "financial_submissions", ["status"], unique=False)

    op.create_table(
        "financial_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("extraction_status", financial_document_status_enum_no_create, nullable=False),
        sa.Column("extracted_data", sa.JSON(), nullable=True),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["financial_submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_financial_documents_submission_id"), "financial_documents", ["submission_id"], unique=False
    )

    op.create_table(
        "infraction_findings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("categorie_infraction", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severite", sa.String(length=20), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["financial_submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_infraction_findings_submission_id"), "infraction_findings", ["submission_id"], unique=False
    )
    op.create_index(
        op.f("ix_infraction_findings_categorie_infraction"),
        "infraction_findings",
        ["categorie_infraction"],
        unique=False,
    )

    op.create_table(
        "infraction_citations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("citation_type", citation_type_enum_no_create, nullable=False),
        sa.Column("ref_id", sa.String(length=100), nullable=False),
        sa.Column("loi", sa.String(length=255), nullable=True),
        sa.Column("numero_article", sa.Integer(), nullable=True),
        sa.Column("reference", sa.String(length=255), nullable=True),
        sa.Column("statut", sa.String(length=50), nullable=True),
        sa.Column("langue", sa.String(length=5), nullable=True),
        sa.Column("extrait", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["infraction_findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_infraction_citations_finding_id"), "infraction_citations", ["finding_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_infraction_citations_finding_id"), table_name="infraction_citations")
    op.drop_table("infraction_citations")

    op.drop_index(op.f("ix_infraction_findings_categorie_infraction"), table_name="infraction_findings")
    op.drop_index(op.f("ix_infraction_findings_submission_id"), table_name="infraction_findings")
    op.drop_table("infraction_findings")

    op.drop_index(op.f("ix_financial_documents_submission_id"), table_name="financial_documents")
    op.drop_table("financial_documents")

    op.drop_index(op.f("ix_financial_submissions_status"), table_name="financial_submissions")
    op.drop_index(op.f("ix_financial_submissions_company_id"), table_name="financial_submissions")
    op.drop_table("financial_submissions")

    op.drop_index(op.f("ix_users_company_id"), table_name="users")
    op.drop_constraint("fk_users_company_id_companies", "users", type_="foreignkey")
    op.drop_column("users", "company_id")

    op.drop_index(op.f("ix_companies_matricule_fiscal"), table_name="companies")
    op.drop_table("companies")

    op.execute("DROP TYPE IF EXISTS citationtype")
    op.execute("DROP TYPE IF EXISTS financialdocumentstatus")
    op.execute("DROP TYPE IF EXISTS financialsubmissionstatus")
    op.execute("DROP TYPE IF EXISTS financialsourcetype")
    # Note: Postgres does not support removing a single value from an enum type, so the
    # 'entreprise' value added to `userrole` in upgrade() is not removed here.
