"""Audit-trail schemas."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_type: str
    agent_name: Optional[str] = None
    actor: str
    severity: str
    summary: Optional[str] = None
    payload: Optional[Any] = None
    created_at: datetime


class AuditTrailResponse(BaseModel):
    encounter_id: str
    events: list[AuditEventOut]
