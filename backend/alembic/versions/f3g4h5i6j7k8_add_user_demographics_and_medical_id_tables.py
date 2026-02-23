"""add user demographics and medical id tables

Revision ID: f3g4h5i6j7k8
Revises: a1b2c3d4e5f6
Create Date: 2026-02-22 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3g4h5i6j7k8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add demographics columns to users table
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("blood_type", sa.String(), nullable=True))
    op.add_column("users", sa.Column("gender", sa.String(), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(), nullable=True))
    op.add_column("users", sa.Column("address", sa.String(), nullable=True))
    op.add_column(
        "users", sa.Column("emergency_contact_name", sa.String(), nullable=True)
    )
    op.add_column(
        "users", sa.Column("emergency_contact_phone", sa.String(), nullable=True)
    )
    op.add_column(
        "users", sa.Column("primary_care_physician", sa.String(), nullable=True)
    )

    # Create medical_id_cards table
    op.create_table(
        "medical_id_cards",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("card_pdf_path", sa.String(), nullable=False),
        sa.Column("qr_code_data", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_medical_id_card_user_id", "medical_id_cards", ["user_id"], unique=False
    )

    # Create temporary_medical_summaries table
    op.create_table(
        "temporary_medical_summaries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("access_token", sa.String(), nullable=False),
        sa.Column("summary_pdf_path", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=True, server_default="5"),
        sa.Column("current_uses", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("is_revoked", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_temp_summary_user_id",
        "temporary_medical_summaries",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_temp_summary_access_token",
        "temporary_medical_summaries",
        ["access_token"],
        unique=True,
    )
    op.create_index(
        "idx_temp_summary_expires_at",
        "temporary_medical_summaries",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "idx_temp_summary_is_revoked",
        "temporary_medical_summaries",
        ["is_revoked"],
        unique=False,
    )


def downgrade() -> None:
    # Drop temporary_medical_summaries table
    op.drop_index(
        "idx_temp_summary_is_revoked", table_name="temporary_medical_summaries"
    )
    op.drop_index(
        "idx_temp_summary_expires_at", table_name="temporary_medical_summaries"
    )
    op.drop_index(
        "idx_temp_summary_access_token", table_name="temporary_medical_summaries"
    )
    op.drop_index("idx_temp_summary_user_id", table_name="temporary_medical_summaries")
    op.drop_table("temporary_medical_summaries")

    # Drop medical_id_cards table
    op.drop_index("idx_medical_id_card_user_id", table_name="medical_id_cards")
    op.drop_table("medical_id_cards")

    # Remove demographics columns from users table
    op.drop_column("users", "primary_care_physician")
    op.drop_column("users", "emergency_contact_phone")
    op.drop_column("users", "emergency_contact_name")
    op.drop_column("users", "address")
    op.drop_column("users", "phone")
    op.drop_column("users", "gender")
    op.drop_column("users", "blood_type")
    op.drop_column("users", "date_of_birth")
