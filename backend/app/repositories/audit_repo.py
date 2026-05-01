"""Audit-event persistence."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import AuditEvent


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def append(
        self,
        *,
        encounter_id: str,
        event_type: str,
        agent_name: Optional[str] = None,
        actor: str = "system",
        severity: str = "info",
        summary: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> AuditEvent:
        evt = AuditEvent(
            encounter_id=encounter_id,
            event_type=event_type,
            agent_name=agent_name,
            actor=actor,
            severity=severity,
            summary=summary,
            payload=payload,
        )
        self.db.add(evt)
        return evt

    def for_encounter(self, encounter_id: str) -> list[AuditEvent]:
        return (
            self.db.query(AuditEvent)
            .filter(AuditEvent.encounter_id == encounter_id)
            .order_by(AuditEvent.created_at.asc())
            .all()
        )
