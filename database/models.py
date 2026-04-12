from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database.database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    audio_filename = Column(String(255), nullable=False)
    raw_transcript_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationship
    generated_notes = relationship("GeneratedNote", back_populates="transcript")


class GeneratedNote(Base):
    __tablename__ = "generated_notes"

    id = Column(Integer, primary_key=True, index=True)
    transcript_id = Column(Integer, ForeignKey("transcripts.id"), nullable=False)
    subjective = Column(Text, nullable=True)
    objective = Column(Text, nullable=True)
    assessment = Column(Text, nullable=True)
    plan = Column(Text, nullable=True)
    raw_gpt4_response = Column(Text, nullable=True)

    # Relationships
    transcript = relationship("Transcript", back_populates="generated_notes")
    physician_edits = relationship("PhysicianEdit", back_populates="note")
    audit_logs = relationship("AuditLog", back_populates="note")


class PhysicianEdit(Base):
    __tablename__ = "physician_edits"

    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("generated_notes.id"), nullable=False)
    section_edited = Column(String(50), nullable=False)  # e.g. 'subjective', 'plan'
    edited_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationship
    note = relationship("GeneratedNote", back_populates="physician_edits")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("generated_notes.id"), nullable=False)
    action_taken = Column(String(255), nullable=False)  # e.g. 'note_generated', 'note_approved'
    who = Column(String(255), nullable=False)           # e.g. physician username
    when = Column(DateTime, default=datetime.utcnow)

    # Relationship
    note = relationship("GeneratedNote", back_populates="audit_logs")
