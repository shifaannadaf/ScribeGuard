"""Transcript persistence."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import Transcript


class TranscriptRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        encounter_id: str,
        raw_text: str,
        formatted_text: Optional[str],
        duration_seconds: Optional[float],
        model: str,
        quality_score: Optional[float] = None,
        quality_issues: Optional[list[str]] = None,
    ) -> Transcript:
        t = Transcript(
            encounter_id=encounter_id,
            raw_text=raw_text,
            formatted_text=formatted_text,
            duration_seconds=duration_seconds,
            model=model,
            quality_score=quality_score,
            quality_issues=quality_issues or [],
            word_count=len(raw_text.split()) if raw_text else 0,
            character_count=len(raw_text or ""),
        )
        self.db.add(t)
        self.db.flush()
        return t

    def latest_for(self, encounter_id: str) -> Optional[Transcript]:
        return (
            self.db.query(Transcript)
            .filter(Transcript.encounter_id == encounter_id)
            .order_by(desc(Transcript.created_at))
            .first()
        )
