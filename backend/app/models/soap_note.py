"""
SOAP note artifact produced by the ClinicalNoteGenerationAgent.

A single encounter may have multiple versions (regenerate / physician edits
spawn new versions); only the version with `is_current=True` is the one the
review UI shows. Older versions are retained for the audit trail.
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean, JSON, Enum as PgEnum
from sqlalchemy.orm import relationship

from app.db.database import Base


class SoapNoteStatus(str, enum.Enum):
    ai_draft         = "ai_draft"           # Fresh from agent — "AI-Generated Pending Review"
    physician_edited = "physician_edited"   # Physician modified at least one section
    approved         = "approved"           # Physician explicitly approved
    superseded       = "superseded"         # A new version replaced this one


class SoapNote(Base):
    __tablename__ = "soap_notes"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
    version      = Column(Integer, nullable=False, default=1)
    is_current   = Column(Boolean, nullable=False, default=True, index=True)

    # SOAP sections
    subjective = Column(Text, nullable=False, default="")
    objective  = Column(Text, nullable=False, default="")
    assessment = Column(Text, nullable=False, default="")
    plan       = Column(Text, nullable=False, default="")

    # Extras the agent emits
    raw_markdown            = Column(Text, nullable=True)        # full markdown render
    low_confidence_sections = Column(JSON, nullable=True)        # ["assessment"], etc.
    flags                   = Column(JSON, nullable=True)        # arbitrary agent flags

    # Provenance
    status      = Column(PgEnum(SoapNoteStatus, name="soap_note_status"), nullable=False, default=SoapNoteStatus.ai_draft)
    model       = Column(String(64), nullable=False)             # e.g. "gpt-4o-mini"
    prompt_version = Column(String(32), nullable=True)
    generated_by_agent = Column(String(64), nullable=True)       # "ClinicalNoteGenerationAgent"

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    encounter   = relationship("Encounter", back_populates="soap_notes")
    medications = relationship("Medication", back_populates="soap_note", cascade="all, delete-orphan")
