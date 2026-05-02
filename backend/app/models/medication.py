"""Structured medication entity emitted by the MedicationExtractionAgent."""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.db.database import Base


class Medication(Base):
    __tablename__ = "medications"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id  = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
    soap_note_id  = Column(Integer, ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=True, index=True)

    # Normalized fields
    name       = Column(String(255), nullable=False)
    dose       = Column(String(100), nullable=True)
    route      = Column(String(64),  nullable=True)
    frequency  = Column(String(100), nullable=True)
    duration   = Column(String(64),  nullable=True)
    start_date = Column(String(20),  nullable=True)
    indication = Column(String(255), nullable=True)

    # Provenance
    raw_text       = Column(String(512), nullable=True)   # Original phrase
    source_section = Column(String(32),  nullable=False, default="plan")
    confidence     = Column(String(16),  nullable=True)   # "high" | "medium" | "low"

    openmrs_resource_uuid = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    encounter = relationship("Encounter", back_populates="medications")
    soap_note = relationship("SoapNote", back_populates="medications")
