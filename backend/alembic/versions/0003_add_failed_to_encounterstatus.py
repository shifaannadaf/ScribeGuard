"""Add 'failed' value to encounterstatus enum.

The encounterstatus type (auto-named by SQLAlchemy from EncounterStatus) was
created without the 'failed' value. This migration adds it.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-01
"""
from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE encounterstatus ADD VALUE IF NOT EXISTS 'failed'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; downgrade is a no-op.
    pass
