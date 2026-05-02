"""Transcript artifact produced by the TranscriptionAgent."""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float, JSON, Integer
from sqlalchemy.orm import relationship

from app.db.database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    encounter_id    = Column(String(64), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)

    raw_text        = Column(Text, nullable=False)              # Direct Whisper output
    formatted_text  = Column(Text, nullable=True)               # Speaker-labelled / cleaned
    duration_seconds = Column(Float, nullable=True)
    model           = Column(String(64), nullable=False)        # e.g. "whisper-1"

    # Quality signals from the agent
    quality_score   = Column(Float, nullable=True)              # 0..1
    quality_issues  = Column(JSON,  nullable=True)              # list[str]

    word_count      = Column(Integer, nullable=True)
    character_count = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    encounter = relationship("Encounter", back_populates="transcripts")
