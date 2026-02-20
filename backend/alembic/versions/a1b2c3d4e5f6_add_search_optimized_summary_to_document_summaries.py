"""Add search_optimized_summary to document_summaries

Revision ID: a1b2c3d4e5f6
Revises: e2e3262da0a2
Create Date: 2026-02-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "e2e3262da0a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_summaries",
        sa.Column("search_optimized_summary", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_summaries", "search_optimized_summary")
