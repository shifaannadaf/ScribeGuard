"""Widen vital_signs.unit from VARCHAR(16) to VARCHAR(64)

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "vital_signs", "unit",
        existing_type=sa.String(16),
        type_=sa.String(64),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "vital_signs", "unit",
        existing_type=sa.String(64),
        type_=sa.String(16),
        existing_nullable=True,
    )
