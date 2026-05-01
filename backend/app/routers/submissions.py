"""
OpenMRS submission endpoint — drives the OpenMRSIntegrationAgent.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories import EncounterRepository, SubmissionRepository
from app.routers._dependencies import get_orchestrator
from app.schemas.submission import SubmitRequest, SubmitResponse


router = APIRouter(prefix="/encounters", tags=["OpenMRS Submission"])


@router.post("/{encounter_id}/submit", response_model=SubmitResponse)
async def submit_to_openmrs(
    encounter_id: str,
    body: SubmitRequest = SubmitRequest(),
    db: Session = Depends(get_db),
    orchestrator = Depends(get_orchestrator),
):
    enc = EncounterRepository(db).get_or_404(encounter_id)

    payload = {}
    if body.openmrs_patient_uuid:
        payload["openmrs_patient_uuid"] = body.openmrs_patient_uuid
    if body.practitioner_uuid:
        payload["practitioner_uuid"] = body.practitioner_uuid

    try:
        result = await orchestrator.run_agent(
            "OpenMRSIntegrationAgent",
            enc,
            actor=body.actor,
            payload=payload,
        )
        output = result.output or {}
        return SubmitResponse(
            encounter_id=enc.id,
            submission_id=int(output.get("submission_id", 0)),
            status="pushed" if output.get("verified", False) else "submitted",
            openmrs_encounter_uuid=output.get("openmrs_encounter_uuid"),
            openmrs_observation_uuid=output.get("openmrs_observation_uuid"),
            attempts=int(result.summary.get("attempts", 1)),
        )
    except Exception as exc:  # noqa: BLE001
        latest = SubmissionRepository(db).latest_for(enc.id)
        return SubmitResponse(
            encounter_id=enc.id,
            submission_id=latest.id if latest else 0,
            status="failed",
            attempts=latest.attempts if latest else 1,
            error=str(exc),
        )


@router.get("/{encounter_id}/submission")
def get_latest_submission(encounter_id: str, db: Session = Depends(get_db)):
    EncounterRepository(db).get_or_404(encounter_id)
    rec = SubmissionRepository(db).latest_for(encounter_id)
    if not rec:
        return {"encounter_id": encounter_id, "submission": None}
    return {
        "encounter_id": encounter_id,
        "submission": {
            "id":                       rec.id,
            "status":                   rec.status.value,
            "attempts":                 rec.attempts,
            "openmrs_patient_uuid":     rec.openmrs_patient_uuid,
            "openmrs_encounter_uuid":   rec.openmrs_encounter_uuid,
            "openmrs_observation_uuid": rec.openmrs_observation_uuid,
            "last_error":               rec.last_error,
            "started_at":               rec.started_at,
            "completed_at":             rec.completed_at,
        },
    }
