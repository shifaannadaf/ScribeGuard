"""
Physician review / edit / approve endpoints.

Every action is routed through the PhysicianReviewAgent so the audit trail
captures who approved what and when.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories import EncounterRepository
from app.routers._dependencies import get_orchestrator
from app.schemas.soap import (
    SoapApproveRequest,
    SoapApproveResponse,
    SoapEditRequest,
)


router = APIRouter(prefix="/encounters", tags=["Physician Review"])


@router.post("/{encounter_id}/review/open")
async def open_review(
    encounter_id: str,
    db: Session = Depends(get_db),
    orchestrator = Depends(get_orchestrator),
):
    enc = EncounterRepository(db).get_or_404(encounter_id)
    result = await orchestrator.run_agent(
        "PhysicianReviewAgent",
        enc,
        actor="physician",
        payload={"action": "open_review"},
    )
    return {"encounter_id": enc.id, **result.summary}


@router.patch("/{encounter_id}/review/edit")
async def edit_soap(
    encounter_id: str,
    body: SoapEditRequest,
    db: Session = Depends(get_db),
    orchestrator = Depends(get_orchestrator),
):
    enc = EncounterRepository(db).get_or_404(encounter_id)
    payload = {
        "action":       "edit",
        "sections":     body.sections.model_dump(exclude_unset=True) if body.sections else {},
        "medications":  [m.model_dump(exclude_unset=True) for m in (body.medications or [])] if body.medications is not None else None,
    }
    result = await orchestrator.run_agent(
        "PhysicianReviewAgent",
        enc,
        actor=body.actor,
        payload=payload,
    )
    return {"encounter_id": enc.id, **result.summary}


@router.post("/{encounter_id}/review/approve", response_model=SoapApproveResponse)
async def approve_soap(
    encounter_id: str,
    body: SoapApproveRequest,
    db: Session = Depends(get_db),
    orchestrator = Depends(get_orchestrator),
):
    enc = EncounterRepository(db).get_or_404(encounter_id)
    result = await orchestrator.run_agent(
        "PhysicianReviewAgent",
        enc,
        actor=body.actor,
        payload={"action": "approve", "comments": body.comments},
    )
    output = result.output or {}
    if not output.get("soap_note_id"):
        raise HTTPException(status_code=400, detail="Approval did not return SOAP note id")
    return SoapApproveResponse(
        encounter_id=enc.id,
        soap_note_id=int(output["soap_note_id"]),
        approved_at=output.get("approved_at") or datetime.now(timezone.utc).isoformat(),
        edits_made=int(output.get("edits_made", 0)),
    )


@router.post("/{encounter_id}/review/revert")
async def revert_approval(
    encounter_id: str,
    db: Session = Depends(get_db),
    orchestrator = Depends(get_orchestrator),
):
    enc = EncounterRepository(db).get_or_404(encounter_id)
    result = await orchestrator.run_agent(
        "PhysicianReviewAgent",
        enc,
        actor="physician",
        payload={"action": "revert"},
    )
    return {"encounter_id": enc.id, **result.summary}
