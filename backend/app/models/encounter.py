"""
Encounter — the root aggregate every agent operates on.

`status` is the user-visible lifecycle (pending / approved / pushed). It is the
stable contract the frontend already understood.

`processing_stage` is the *agentic* fine-grained state the orchestrator advances
as each agent completes. It is what powers the live pipeline visualization.
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Enum as PgEnum
from sqlalchemy.orm import relationship

from app.db.database import Base


class EncounterStatus(str, enum.Enum):
    pending  = "pending"      # AI draft awaiting physician review
    approved = "approved"     # Physician approved, ready to submit
    pushed   = "pushed"       # Submitted to OpenMRS
    failed   = "failed"       # Terminal failure


class ProcessingStage(str, enum.Enum):
    """Fine-grained agentic pipeline state — drives the orchestrator."""
    created            = "created"
    audio_received     = "audio_received"
    transcribing       = "transcribing"
    transcribed        = "transcribed"
    generating_soap    = "generating_soap"
    soap_drafted       = "soap_drafted"
    extracting_meds    = "extracting_meds"
    ready_for_review   = "ready_for_review"
    in_review          = "in_review"
    approved           = "approved"
    submitting         = "submitting"
    submitted          = "submitted"
    failed             = "failed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Encounter(Base):
    __tablename__ = "encounters"

    # Identity
    id           = Column(String(64), primary_key=True)            # UUID
    patient_name = Column(String(255), nullable=False)
    patient_id   = Column(String(50),  nullable=False)             # local clinic ID
    openmrs_patient_uuid = Column(String(64), nullable=True)       # FHIR Patient/{uuid}

    # Audio metadata (the raw file lives on disk; we never store bytes in PG)
    audio_filename     = Column(String(255), nullable=True)
    audio_path         = Column(String(512), nullable=True)
    audio_size_bytes   = Column(String(32),  nullable=True)        # str to avoid bigint mismatches
    audio_mime         = Column(String(64),  nullable=True)
    audio_duration_sec = Column(String(32),  nullable=True)

    # Pipeline state
    status           = Column(PgEnum(EncounterStatus, name="encounter_status"), nullable=False, default=EncounterStatus.pending)
    processing_stage = Column(PgEnum(ProcessingStage, name="processing_stage"), nullable=False, default=ProcessingStage.created)
    last_error       = Column(Text, nullable=True)

    # Convenience field — kept for backward compatibility with the frontend
    duration   = Column(String(32),  nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships ─────────────────────────────────────────────────────
    transcripts          = relationship("Transcript",          back_populates="encounter", cascade="all, delete-orphan", order_by="Transcript.created_at.desc()")
    soap_notes           = relationship("SoapNote",            back_populates="encounter", cascade="all, delete-orphan", order_by="SoapNote.version.desc()")
    medications          = relationship("Medication",          back_populates="encounter", cascade="all, delete-orphan")
    allergies            = relationship("Allergy",             back_populates="encounter", cascade="all, delete-orphan")
    conditions           = relationship("Condition",           back_populates="encounter", cascade="all, delete-orphan")
    vital_signs          = relationship("VitalSign",           back_populates="encounter", cascade="all, delete-orphan")
    follow_ups           = relationship("FollowUp",            back_populates="encounter", cascade="all, delete-orphan")
    patient_context_snapshots = relationship("PatientContext", back_populates="encounter", cascade="all, delete-orphan", order_by="PatientContext.fetched_at.desc()")
    physician_edits      = relationship("PhysicianEdit",       back_populates="encounter", cascade="all, delete-orphan")
    physician_approvals  = relationship("PhysicianApproval",   back_populates="encounter", cascade="all, delete-orphan")
    submission_records   = relationship("SubmissionRecord",    back_populates="encounter", cascade="all, delete-orphan", order_by="SubmissionRecord.started_at.desc()")
    agent_runs           = relationship("AgentRun",            back_populates="encounter", cascade="all, delete-orphan", order_by="AgentRun.started_at.asc()")
    audit_events         = relationship("AuditEvent",          back_populates="encounter", cascade="all, delete-orphan", order_by="AuditEvent.created_at.asc()")

    # ── Convenience accessors ─────────────────────────────────────────
    @property
    def latest_transcript(self):
        return self.transcripts[0] if self.transcripts else None

    @property
    def current_soap_note(self):
        for n in self.soap_notes:
            if n.is_current:
                return n
        return self.soap_notes[0] if self.soap_notes else None

    @property
    def latest_submission(self):
        return self.submission_records[0] if self.submission_records else None

    @property
    def latest_patient_context(self):
        return self.patient_context_snapshots[0] if self.patient_context_snapshots else None
