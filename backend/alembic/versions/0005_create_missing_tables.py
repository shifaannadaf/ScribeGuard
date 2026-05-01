"""Create all tables that exist in models but not in the DB.

The DB was bootstrapped from an older schema via create_all(). This migration
uses create_all(checkfirst=True) to create every missing table (transcripts,
audit_events, soap_notes, agent_runs, submission_records, physician_edits,
physician_approvals) and their associated enum types without touching
tables that already exist.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-01
"""
from __future__ import annotations

from alembic import op
from app.db.database import Base

# Import all models so their metadata is registered before create_all runs.
import app.models  # noqa: F401

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    # Intentionally a no-op — dropping tables here would destroy data.
    pass
