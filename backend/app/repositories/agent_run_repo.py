"""Agent-run persistence."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import AgentRun, AgentRunStatus


class AgentRunRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_running(
        self,
        *,
        encounter_id: str,
        agent_name: str,
        agent_version: str,
        attempt: int,
        input_summary: Optional[dict[str, Any]] = None,
    ) -> AgentRun:
        run = AgentRun(
            encounter_id=encounter_id,
            agent_name=agent_name,
            agent_version=agent_version,
            status=AgentRunStatus.running,
            attempt=attempt,
            input_summary=input_summary,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def finish(
        self,
        run: AgentRun,
        *,
        status: AgentRunStatus,
        output_summary: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> AgentRun:
        run.status = status
        run.output_summary = output_summary
        run.error_message = error_message
        run.error_type = error_type
        run.finished_at = datetime.now(timezone.utc)
        run.duration_ms = duration_ms
        return run

    def for_encounter(self, encounter_id: str) -> list[AgentRun]:
        return (
            self.db.query(AgentRun)
            .filter(AgentRun.encounter_id == encounter_id)
            .order_by(AgentRun.started_at.asc())
            .all()
        )
