"""
OpenMRS submission record — what the OpenMRSIntegrationAgent emitted, including
retries and verification state. This is the system-of-record audit row that
proves write-back happened (or didn't).
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, JSON, Enum as PgEnum
from sqlalchemy.orm import relationship

from app.db.database import Base


class SubmissionStatus(str, enum.Enum):
    pending   = "pending"
    in_flight = "in_flight"
    success   = "success"
    failed    = "failed"
    verified  = "verified"


class SubmissionRecord(Base):
    __tablename__ = "submission_records"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id  = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
    soap_note_id  = Column(Integer,  ForeignKey("soap_notes.id", ondelete="SET NULL"), nullable=True)

    # OpenMRS-side identifiers
    openmrs_patient_uuid    = Column(String(64), nullable=True)
    openmrs_encounter_uuid  = Column(String(64), nullable=True)
    openmrs_observation_uuid = Column(String(64), nullable=True)

    # State
    status   = Column(PgEnum(SubmissionStatus, name="submission_status"), nullable=False, default=SubmissionStatus.pending)
    attempts = Column(Integer, nullable=False, default=0)

    # Payload + provenance
    fhir_payload = Column(JSON, nullable=True)
    fhir_response = Column(JSON, nullable=True)
    last_error   = Column(Text, nullable=True)

    started_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    encounter = relationship("Encounter", back_populates="submission_records")
