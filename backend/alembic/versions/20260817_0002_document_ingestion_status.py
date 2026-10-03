"""document ingestion status

Revision ID: 20260817_0002
Revises: 20260723_0001
Create Date: 2026-08-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260817_0002"
down_revision = "20260723_0001"
branch_labels = None
depends_on = None


ingestion_status_enum_no_create = postgresql.ENUM(
    "uploaded", "processing", "indexed", "failed", name="ingestionstatus", create_type=False
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ingestionstatus') THEN
                CREATE TYPE ingestionstatus AS ENUM ('uploaded', 'processing', 'indexed', 'failed');
            END IF;
        END
        $$;
        """
    )

    op.add_column(
        "documents_metadata",
        sa.Column("original_filename", sa.String(length=500), nullable=False, server_default=""),
    )
    op.add_column(
        "documents_metadata",
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "documents_metadata",
        sa.Column(
            "ingestion_status",
            ingestion_status_enum_no_create,
            nullable=False,
            server_default="uploaded",
        ),
    )
    op.add_column(
        "documents_metadata",
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "documents_metadata",
        sa.Column("ingestion_error", sa.Text(), nullable=True),
    )
    op.create_index(
        op.f("ix_documents_metadata_ingestion_status"),
        "documents_metadata",
        ["ingestion_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_metadata_ingestion_status"), table_name="documents_metadata")
    op.drop_column("documents_metadata", "ingestion_error")
    op.drop_column("documents_metadata", "chunk_count")
    op.drop_column("documents_metadata", "ingestion_status")
    op.drop_column("documents_metadata", "size_bytes")
    op.drop_column("documents_metadata", "original_filename")
    op.execute("DROP TYPE IF EXISTS ingestionstatus")
