"""Add openmrs_resource_uuid to medications table

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "medications",
        sa.Column("openmrs_resource_uuid", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("medications", "openmrs_resource_uuid")
