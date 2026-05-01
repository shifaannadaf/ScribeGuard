"""
High-level audit event stream. Whereas `agent_runs` records the *technical*
execution of every agent, `audit_events` is the *clinical/business* trail
required for traceability and future compliance review.

The AuditTraceabilityAgent owns the writes to this table.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship

from app.db.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type   = Column(String(64), nullable=False, index=True)   # e.g. transcript_created, soap_generated
    agent_name   = Column(String(80), nullable=True)
    actor        = Column(String(128), nullable=False, default="system")
    severity     = Column(String(16), nullable=False, default="info")   # info | warning | error

    summary      = Column(String(512), nullable=True)
    payload      = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    encounter = relationship("Encounter", back_populates="audit_events")
