import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, ForeignKey,
    Enum as PgEnum, JSON
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class EncounterStatus(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    pushed   = "pushed"


class Encounter(Base):
    __tablename__ = "encounters"

    id             = Column(String, primary_key=True)           # UUID
    patient_name   = Column(String(255), nullable=False)
    patient_id     = Column(String(50),  nullable=False)        # e.g. P-00123
    openmrs_uuid   = Column(String(255), nullable=True)         # linked at push time
    audio_filename = Column(String(255), nullable=True)
    transcript     = Column(Text,        nullable=True)
    duration       = Column(String(20),  nullable=True)         # e.g. "4m 32s"
    status         = Column(PgEnum(EncounterStatus), nullable=False, default=EncounterStatus.pending)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    medications  = relationship("Medication",  back_populates="encounter", cascade="all, delete-orphan")
    allergies    = relationship("Allergy",     back_populates="encounter", cascade="all, delete-orphan")
    diagnoses    = relationship("Diagnosis",   back_populates="encounter", cascade="all, delete-orphan")
    audit_logs   = relationship("AuditLog",    back_populates="encounter", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="encounter", cascade="all, delete-orphan")


class Medication(Base):
    __tablename__ = "medications"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id = Column(String, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    name         = Column(String(255), nullable=False)
    dose         = Column(String(100), nullable=True)
    route        = Column(String(100), nullable=True)
    frequency    = Column(String(100), nullable=True)
    start_date   = Column(String(20),  nullable=True)

    encounter = relationship("Encounter", back_populates="medications")


class Allergy(Base):
    __tablename__ = "allergies"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id = Column(String, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    allergen     = Column(String(255), nullable=False)
    reaction     = Column(String(255), nullable=True)
    severity     = Column(String(50),  nullable=True)   # Mild / Moderate / Severe

    encounter = relationship("Encounter", back_populates="allergies")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id = Column(String, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    icd10_code   = Column(String(20),  nullable=True)
    description  = Column(String(500), nullable=False)
    status       = Column(String(50),  nullable=True)   # Presumed / Confirmed / Ruled Out

    encounter = relationship("Encounter", back_populates="diagnoses")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id = Column(String, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    action       = Column(String(100), nullable=False)  # created / approved / reverted / pushed / edited
    actor        = Column(String(100), nullable=False, default="guest")
    detail       = Column(JSON,        nullable=True)   # optional extra context
    timestamp    = Column(DateTime, default=datetime.utcnow, nullable=False)

    encounter = relationship("Encounter", back_populates="audit_logs")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id = Column(String, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    role         = Column(String(20),  nullable=False)  # user / assistant
    content      = Column(Text,        nullable=False)
    timestamp    = Column(DateTime, default=datetime.utcnow, nullable=False)

    encounter = relationship("Encounter", back_populates="chat_messages")
