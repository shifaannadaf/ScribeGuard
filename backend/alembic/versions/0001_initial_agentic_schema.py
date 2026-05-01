"""Initial agentic schema.

Creates the full ScribeGuard production schema:
    - encounters (with `processing_stage` for the orchestrator)
    - transcripts
    - soap_notes (versioned)
    - medications
    - physician_edits, physician_approvals
    - submission_records
    - agent_runs
    - audit_events

Revision ID: 0001
Revises:
Create Date: 2026-04-29
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


encounter_status     = sa.Enum("pending", "approved", "pushed", "failed", name="encounter_status")
processing_stage     = sa.Enum(
    "created", "audio_received", "transcribing", "transcribed",
    "generating_soap", "soap_drafted", "extracting_meds", "ready_for_review",
    "in_review", "approved", "submitting", "submitted", "failed",
    name="processing_stage",
)
soap_note_status     = sa.Enum("ai_draft", "physician_edited", "approved", "superseded", name="soap_note_status")
submission_status    = sa.Enum("pending", "in_flight", "success", "failed", "verified", name="submission_status")
agent_run_status     = sa.Enum("queued", "running", "succeeded", "failed", "skipped", name="agent_run_status")


def upgrade() -> None:
    bind = op.get_bind()
    encounter_status.create(bind, checkfirst=True)
    processing_stage.create(bind, checkfirst=True)
    soap_note_status.create(bind, checkfirst=True)
    submission_status.create(bind, checkfirst=True)
    agent_run_status.create(bind, checkfirst=True)

    op.create_table(
        "encounters",
        sa.Column("id",                   sa.String(64), primary_key=True),
        sa.Column("patient_name",         sa.String(255), nullable=False),
        sa.Column("patient_id",           sa.String(50),  nullable=False),
        sa.Column("openmrs_patient_uuid", sa.String(64),  nullable=True),
        sa.Column("audio_filename",       sa.String(255), nullable=True),
        sa.Column("audio_path",           sa.String(512), nullable=True),
        sa.Column("audio_size_bytes",     sa.String(32),  nullable=True),
        sa.Column("audio_mime",           sa.String(64),  nullable=True),
        sa.Column("audio_duration_sec",   sa.String(32),  nullable=True),
        sa.Column("status",               encounter_status, nullable=False, server_default="pending"),
        sa.Column("processing_stage",     processing_stage, nullable=False, server_default="created"),
        sa.Column("last_error",           sa.Text, nullable=True),
        sa.Column("duration",             sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "transcripts",
        sa.Column("id",               sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id",     sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("raw_text",         sa.Text, nullable=False),
        sa.Column("formatted_text",   sa.Text, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("model",            sa.String(64), nullable=False),
        sa.Column("quality_score",    sa.Float, nullable=True),
        sa.Column("quality_issues",   sa.JSON,  nullable=True),
        sa.Column("word_count",       sa.Integer, nullable=True),
        sa.Column("character_count",  sa.Integer, nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "soap_notes",
        sa.Column("id",                       sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id",             sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version",                  sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_current",               sa.Boolean, nullable=False, server_default=sa.text("true"), index=True),
        sa.Column("subjective",               sa.Text, nullable=False, server_default=""),
        sa.Column("objective",                sa.Text, nullable=False, server_default=""),
        sa.Column("assessment",               sa.Text, nullable=False, server_default=""),
        sa.Column("plan",                     sa.Text, nullable=False, server_default=""),
        sa.Column("raw_markdown",             sa.Text, nullable=True),
        sa.Column("low_confidence_sections",  sa.JSON, nullable=True),
        sa.Column("flags",                    sa.JSON, nullable=True),
        sa.Column("status",                   soap_note_status, nullable=False, server_default="ai_draft"),
        sa.Column("model",                    sa.String(64), nullable=False),
        sa.Column("prompt_version",           sa.String(32), nullable=True),
        sa.Column("generated_by_agent",       sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "medications",
        sa.Column("id",             sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id",   sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("soap_note_id",   sa.Integer, sa.ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("name",           sa.String(255), nullable=False),
        sa.Column("dose",           sa.String(100), nullable=True),
        sa.Column("route",          sa.String(64),  nullable=True),
        sa.Column("frequency",      sa.String(100), nullable=True),
        sa.Column("duration",       sa.String(64),  nullable=True),
        sa.Column("start_date",     sa.String(20),  nullable=True),
        sa.Column("indication",     sa.String(255), nullable=True),
        sa.Column("raw_text",       sa.String(512), nullable=True),
        sa.Column("source_section", sa.String(32),  nullable=False, server_default="plan"),
        sa.Column("confidence",     sa.String(16),  nullable=True),
        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "physician_edits",
        sa.Column("id",            sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id",  sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("soap_note_id",  sa.Integer, sa.ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("section",       sa.String(32), nullable=False),
        sa.Column("original_text", sa.Text, nullable=True),
        sa.Column("edited_text",   sa.Text, nullable=True),
        sa.Column("actor",         sa.String(128), nullable=False, server_default="physician"),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "physician_approvals",
        sa.Column("id",            sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id",  sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("soap_note_id",  sa.Integer, sa.ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor",         sa.String(128), nullable=False, server_default="physician"),
        sa.Column("comments",      sa.Text, nullable=True),
        sa.Column("edits_made",    sa.Integer, nullable=False, server_default="0"),
        sa.Column("approved_at",   sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "submission_records",
        sa.Column("id",                       sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id",             sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("soap_note_id",             sa.Integer, sa.ForeignKey("soap_notes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("openmrs_patient_uuid",     sa.String(64), nullable=True),
        sa.Column("openmrs_encounter_uuid",   sa.String(64), nullable=True),
        sa.Column("openmrs_observation_uuid", sa.String(64), nullable=True),
        sa.Column("status",                   submission_status, nullable=False, server_default="pending"),
        sa.Column("attempts",                 sa.Integer, nullable=False, server_default="0"),
        sa.Column("fhir_payload",             sa.JSON, nullable=True),
        sa.Column("fhir_response",            sa.JSON, nullable=True),
        sa.Column("last_error",               sa.Text, nullable=True),
        sa.Column("started_at",               sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at",             sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id",             sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id",   sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_name",     sa.String(80), nullable=False, index=True),
        sa.Column("agent_version",  sa.String(32), nullable=True),
        sa.Column("status",         agent_run_status, nullable=False, server_default="queued"),
        sa.Column("attempt",        sa.Integer, nullable=False, server_default="1"),
        sa.Column("input_summary",  sa.JSON, nullable=True),
        sa.Column("output_summary", sa.JSON, nullable=True),
        sa.Column("error_message",  sa.Text, nullable=True),
        sa.Column("error_type",     sa.String(128), nullable=True),
        sa.Column("started_at",     sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms",    sa.Float, nullable=True),
    )

    op.create_table(
        "audit_events",
        sa.Column("id",           sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("encounter_id", sa.String(64), sa.ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event_type",   sa.String(64), nullable=False, index=True),
        sa.Column("agent_name",   sa.String(80), nullable=True),
        sa.Column("actor",        sa.String(128), nullable=False, server_default="system"),
        sa.Column("severity",     sa.String(16), nullable=False, server_default="info"),
        sa.Column("summary",      sa.String(512), nullable=True),
        sa.Column("payload",      sa.JSON, nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    for t in (
        "audit_events",
        "agent_runs",
        "submission_records",
        "physician_approvals",
        "physician_edits",
        "medications",
        "soap_notes",
        "transcripts",
        "encounters",
    ):
        op.drop_table(t)

    bind = op.get_bind()
    for enum in (agent_run_status, submission_status, soap_note_status, processing_stage, encounter_status):
        enum.drop(bind, checkfirst=True)
