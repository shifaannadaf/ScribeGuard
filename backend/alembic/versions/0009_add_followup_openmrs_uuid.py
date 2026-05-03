"""Add openmrs_resource_uuid to follow_ups table

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "follow_ups",
        sa.Column("openmrs_resource_uuid", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("follow_ups", "openmrs_resource_uuid")
