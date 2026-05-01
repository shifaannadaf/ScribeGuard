"""Clinical entities + patient context snapshot.

Adds:
    - allergies
    - conditions
    - vital_signs
    - follow_ups
    - patient_contexts

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-30
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "allergies",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id", sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("soap_note_id", sa.Integer, sa.ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("substance",  sa.String(255), nullable=False),
        sa.Column("reaction",   sa.String(255), nullable=True),
        sa.Column("severity",   sa.String(32),  nullable=True),
        sa.Column("category",   sa.String(32),  nullable=True),
        sa.Column("onset",      sa.String(64),  nullable=True),
        sa.Column("confidence", sa.String(16),  nullable=True),
        sa.Column("raw_text",   sa.String(512), nullable=True),
        sa.Column("openmrs_resource_uuid", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "conditions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id", sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("soap_note_id", sa.Integer, sa.ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("description",     sa.String(500), nullable=False),
        sa.Column("icd10_code",      sa.String(20),  nullable=True),
        sa.Column("snomed_code",     sa.String(32),  nullable=True),
        sa.Column("clinical_status", sa.String(32),  nullable=True),
        sa.Column("verification",    sa.String(32),  nullable=True),
        sa.Column("onset",           sa.String(64),  nullable=True),
        sa.Column("note",            sa.Text,        nullable=True),
        sa.Column("confidence",      sa.String(16),  nullable=True),
        sa.Column("raw_text",        sa.String(512), nullable=True),
        sa.Column("openmrs_resource_uuid", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "vital_signs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id", sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("soap_note_id", sa.Integer, sa.ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("kind",        sa.String(32),  nullable=False),
        sa.Column("value",       sa.Float,       nullable=False),
        sa.Column("unit",        sa.String(16),  nullable=True),
        sa.Column("measured_at", sa.String(64),  nullable=True),
        sa.Column("confidence",  sa.String(16),  nullable=True),
        sa.Column("raw_text",    sa.String(255), nullable=True),
        sa.Column("openmrs_resource_uuid", sa.String(64), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "follow_ups",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id", sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("soap_note_id", sa.Integer, sa.ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("description",   sa.Text,        nullable=False),
        sa.Column("interval",      sa.String(64),  nullable=True),
        sa.Column("target_date",   sa.String(32),  nullable=True),
        sa.Column("with_provider", sa.String(255), nullable=True),
        sa.Column("confidence",    sa.String(16),  nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "patient_contexts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id", sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("fetched_at",         sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("patient_uuid",       sa.String(64), nullable=True),
        sa.Column("patient_demographics", sa.JSON, nullable=True),
        sa.Column("existing_medications", sa.JSON, nullable=True),
        sa.Column("existing_allergies",   sa.JSON, nullable=True),
        sa.Column("existing_conditions",  sa.JSON, nullable=True),
        sa.Column("recent_observations",  sa.JSON, nullable=True),
        sa.Column("recent_encounters",    sa.JSON, nullable=True),
        sa.Column("fetch_errors",         sa.JSON, nullable=True),
    )


def downgrade() -> None:
    for t in ("patient_contexts", "follow_ups", "vital_signs", "conditions", "allergies"):
        op.drop_table(t)
