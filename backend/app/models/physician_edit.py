"""
Physician-in-the-loop tracking — every section edit and every approval is
captured here so we have a defensible audit trail of "what the AI said vs what
the physician committed".
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.db.database import Base


class PhysicianEdit(Base):
    __tablename__ = "physician_edits"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id  = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
    soap_note_id  = Column(Integer,  ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=False, index=True)

    section       = Column(String(32), nullable=False)         # subjective / objective / assessment / plan / medications
    original_text = Column(Text, nullable=True)
    edited_text   = Column(Text, nullable=True)
    actor         = Column(String(128), nullable=False, default="physician")
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    encounter = relationship("Encounter", back_populates="physician_edits")


class PhysicianApproval(Base):
    __tablename__ = "physician_approvals"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id  = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
    soap_note_id  = Column(Integer,  ForeignKey("soap_notes.id", ondelete="CASCADE"), nullable=False)

    actor      = Column(String(128), nullable=False, default="physician")
    comments   = Column(Text, nullable=True)
    edits_made = Column(Integer, nullable=False, default=0)
    approved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    encounter = relationship("Encounter", back_populates="physician_approvals")
