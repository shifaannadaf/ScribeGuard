"""
Clinical entities the ClinicalEntityExtractionAgent classifies from a SOAP
note.

Each entity type maps 1:1 onto a FHIR R4 resource the OpenMRSIntegrationAgent
writes back:

    Allergy        → AllergyIntolerance
    Condition      → Condition (with ICD-10 + SNOMED)
    VitalSign      → Observation (vital-signs)
    FollowUp       → free-text in the SOAP plan + a CarePlan in the future
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, ForeignKey, DateTime, Float, JSON,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Allergy(Base):
    __tablename__ = "allergies"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id  = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
    soap_note_id  = Column(Integer, ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=True, index=True)

    substance        = Column(String(255), nullable=False)            # e.g. "Penicillin"
    reaction         = Column(String(255), nullable=True)             # e.g. "rash", "anaphylaxis"
    severity         = Column(String(32),  nullable=True)             # "mild" | "moderate" | "severe"
    category         = Column(String(32),  nullable=True)             # "medication" | "food" | "environmental"
    onset            = Column(String(64),  nullable=True)
    confidence       = Column(String(16),  nullable=True)
    raw_text         = Column(String(512), nullable=True)

    # OpenMRS write-back trail
    openmrs_resource_uuid = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    encounter = relationship("Encounter", back_populates="allergies")


class Condition(Base):
    """A diagnosis / clinical condition extracted from the Assessment section."""
    __tablename__ = "conditions"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id  = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
    soap_note_id  = Column(Integer, ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=True, index=True)

    description       = Column(String(500), nullable=False)
    icd10_code        = Column(String(20),  nullable=True)
    snomed_code       = Column(String(32),  nullable=True)
    clinical_status   = Column(String(32),  nullable=True)            # "active" | "inactive" | "resolved"
    verification      = Column(String(32),  nullable=True)            # "confirmed" | "provisional" | "differential"
    onset             = Column(String(64),  nullable=True)
    note              = Column(Text,        nullable=True)
    confidence        = Column(String(16),  nullable=True)
    raw_text          = Column(String(512), nullable=True)

    openmrs_resource_uuid = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    encounter = relationship("Encounter", back_populates="conditions")


class VitalSign(Base):
    """A single vital-sign observation (height, weight, BP, HR, temp, RR, SpO2)."""
    __tablename__ = "vital_signs"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id  = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
    soap_note_id  = Column(Integer, ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=True, index=True)

    kind        = Column(String(32),  nullable=False)                 # "height"|"weight"|"temperature"|"respiratory_rate"|"spo2"|"hr"|"systolic_bp"|"diastolic_bp"
    value       = Column(Float,       nullable=False)
    unit        = Column(String(16),  nullable=True)
    measured_at = Column(String(64),  nullable=True)                  # ISO when stated, else null
    confidence  = Column(String(16),  nullable=True)
    raw_text    = Column(String(255), nullable=True)

    openmrs_resource_uuid = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    encounter = relationship("Encounter", back_populates="vital_signs")


class FollowUp(Base):
    """Follow-up instructions extracted from the Plan section."""
    __tablename__ = "follow_ups"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id  = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
    soap_note_id  = Column(Integer, ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=True, index=True)

    description    = Column(Text,        nullable=False)               # "Follow up in 3 months"
    interval       = Column(String(64),  nullable=True)                # "3 months"
    target_date    = Column(String(32),  nullable=True)                # ISO if explicit
    with_provider  = Column(String(255), nullable=True)
    confidence     = Column(String(16),  nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    encounter = relationship("Encounter", back_populates="follow_ups")


class PatientContext(Base):
    """
    Snapshot of the existing OpenMRS patient record taken by the
    OpenMRSPatientContextAgent at the start of an encounter so the physician
    sees the patient's chart context inline. Snapshotting (vs. always
    fetching live) means the review UI is fast and that we have a durable
    record of what the AI saw at submission time.
    """
    __tablename__ = "patient_contexts"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id  = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)

    fetched_at        = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    patient_uuid      = Column(String(64), nullable=True)
    patient_demographics = Column(JSON,  nullable=True)
    existing_medications = Column(JSON,  nullable=True)
    existing_allergies   = Column(JSON,  nullable=True)
    existing_conditions  = Column(JSON,  nullable=True)
    recent_observations  = Column(JSON,  nullable=True)
    recent_encounters    = Column(JSON,  nullable=True)
    fetch_errors         = Column(JSON,  nullable=True)

    encounter = relationship("Encounter", back_populates="patient_context_snapshots")
