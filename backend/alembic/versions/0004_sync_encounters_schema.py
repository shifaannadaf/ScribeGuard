"""Sync encounters table to current model.

The DB was bootstrapped via create_all() from an older schema. This migration
adds all columns that exist in the model but not in the DB:
  - Rename openmrs_uuid -> openmrs_patient_uuid
  - Add audio_path, audio_size_bytes, audio_mime, audio_duration_sec
  - Create processing_stage enum and add processing_stage column
  - Add last_error column

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_PROCESSING_STAGE_VALUES = (
    "created", "audio_received", "transcribing", "transcribed",
    "generating_soap", "soap_drafted", "extracting_meds",
    "ready_for_review", "in_review", "approved",
    "submitting", "submitted", "failed",
)

processing_stage_enum = sa.Enum(*_PROCESSING_STAGE_VALUES, name="processing_stage")


def upgrade() -> None:
    # Rename the old openmrs_uuid column
    op.alter_column("encounters", "openmrs_uuid", new_column_name="openmrs_patient_uuid")

    # Add missing audio metadata columns
    op.add_column("encounters", sa.Column("audio_path",         sa.String(512), nullable=True))
    op.add_column("encounters", sa.Column("audio_size_bytes",   sa.String(32),  nullable=True))
    op.add_column("encounters", sa.Column("audio_mime",         sa.String(64),  nullable=True))
    op.add_column("encounters", sa.Column("audio_duration_sec", sa.String(32),  nullable=True))

    # Create the processing_stage enum and column
    processing_stage_enum.create(op.get_bind(), checkfirst=True)
    op.add_column("encounters", sa.Column(
        "processing_stage",
        processing_stage_enum,
        nullable=False,
        server_default="created",
    ))

    # Add last_error column
    op.add_column("encounters", sa.Column("last_error", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("encounters", "last_error")
    op.drop_column("encounters", "processing_stage")
    processing_stage_enum.drop(op.get_bind(), checkfirst=True)
    op.drop_column("encounters", "audio_duration_sec")
    op.drop_column("encounters", "audio_mime")
    op.drop_column("encounters", "audio_size_bytes")
    op.drop_column("encounters", "audio_path")
    op.alter_column("encounters", "openmrs_patient_uuid", new_column_name="openmrs_uuid")
