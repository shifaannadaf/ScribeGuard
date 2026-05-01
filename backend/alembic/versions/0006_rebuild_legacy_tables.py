"""Rebuild medications and allergies with the current model schema.

Both tables were created from a much older schema by create_all() and are
missing many columns the current code requires (soap_note_id, created_at,
confidence, raw_text, etc.). The legacy schemas are too divergent to ALTER
into the current shape, so this migration drops them and lets create_all()
recreate them from the current models. Test data in those tables is lost.

Legacy tables not referenced by current models (audit_log, chat_messages,
diagnoses) are left untouched — they're harmless dead weight.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-01
"""
from __future__ import annotations

from alembic import op
from app.db.database import Base

import app.models  # noqa: F401  (registers all models on Base.metadata)

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Drop the two legacy tables whose schemas can't be cleanly migrated.
    op.execute("DROP TABLE IF EXISTS medications CASCADE")
    op.execute("DROP TABLE IF EXISTS allergies CASCADE")

    # Recreate every model-defined table that doesn't already exist.
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    # Intentionally a no-op — we cannot reconstruct the legacy schemas.
    pass
