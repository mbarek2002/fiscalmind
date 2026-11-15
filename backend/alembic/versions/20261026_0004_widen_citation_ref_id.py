"""widen infraction_citations.ref_id

Revision ID: 20261026_0004
Revises: 20260909_0003
Create Date: 2026-10-26 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20261026_0004"
down_revision = "20260909_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The by-article chunking pipeline uses "{source_file}::chunk{index}" as its
    # chunk/article identifier, which exceeds 100 chars for long real filenames
    # in the corpus -- the old pipeline's short UUID-based ids never hit this.
    op.alter_column(
        "infraction_citations",
        "ref_id",
        existing_type=sa.String(length=100),
        type_=sa.String(length=500),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "infraction_citations",
        "ref_id",
        existing_type=sa.String(length=500),
        type_=sa.String(length=100),
        existing_nullable=False,
    )
