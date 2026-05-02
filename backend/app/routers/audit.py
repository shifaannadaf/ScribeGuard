"""Audit-trail endpoints — driven by the AuditTraceabilityAgent."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories import AuditRepository, EncounterRepository
from app.routers._dependencies import get_orchestrator
from app.schemas.audit import AuditEventOut, AuditTrailResponse


router = APIRouter(prefix="/encounters", tags=["Audit"])


@router.get("/{encounter_id}/audit", response_model=AuditTrailResponse)
def get_audit_trail(encounter_id: str, db: Session = Depends(get_db)):
    EncounterRepository(db).get_or_404(encounter_id)
    events = AuditRepository(db).for_encounter(encounter_id)
    return AuditTrailResponse(
        encounter_id=encounter_id,
        events=[AuditEventOut.model_validate(e) for e in events],
    )


@router.get("/{encounter_id}/audit/timeline")
async def get_audit_timeline(
    encounter_id: str,
    db: Session = Depends(get_db),
    orchestrator = Depends(get_orchestrator),
):
    enc = EncounterRepository(db).get_or_404(encounter_id)
    result = await orchestrator.run_agent(
        "AuditTraceabilityAgent",
        enc,
        actor="system",
    )
    return {"encounter_id": encounter_id, **(result.output or {})}
