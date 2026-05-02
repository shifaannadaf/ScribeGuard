"""
Per-agent execution record. The orchestrator writes one row per agent
invocation so the entire pipeline is observable, debuggable, and
reproducible.
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, JSON, Float, Enum as PgEnum
from sqlalchemy.orm import relationship

from app.db.database import Base


class AgentRunStatus(str, enum.Enum):
    queued    = "queued"
    running   = "running"
    succeeded = "succeeded"
    failed    = "failed"
    skipped   = "skipped"


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)

    agent_name   = Column(String(80), nullable=False, index=True)
    agent_version = Column(String(32), nullable=True)

    status   = Column(PgEnum(AgentRunStatus, name="agent_run_status"), nullable=False, default=AgentRunStatus.queued)
    attempt  = Column(Integer, nullable=False, default=1)

    # Compact summaries — full payloads live in the relevant artifact tables
    input_summary  = Column(JSON, nullable=True)
    output_summary = Column(JSON, nullable=True)
    error_message  = Column(Text, nullable=True)
    error_type     = Column(String(128), nullable=True)

    started_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Float, nullable=True)

    encounter = relationship("Encounter", back_populates="agent_runs")
