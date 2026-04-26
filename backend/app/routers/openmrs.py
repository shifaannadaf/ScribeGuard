from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Encounter, AuditLog, EncounterStatus
from app.schemas.misc import OpenMRSPatient, PushRequest, PushResponse

router = APIRouter(tags=["OpenMRS"])


@router.get("/openmrs/patients/{patient_id}", response_model=OpenMRSPatient)
def get_openmrs_patient(patient_id: str):
    # Stub — real OpenMRS GET goes here
    return OpenMRSPatient(
        uuid="openmrs-mock-uuid-001",
        name="John Doe",
        identifier=patient_id,
        birthdate="1985-06-12",
        gender="M",
        active_medications=[],
        known_allergies=[],
    )


@router.post("/encounters/{encounter_id}/push", response_model=PushResponse)
def push_to_openmrs(encounter_id: str, body: PushRequest, db: Session = Depends(get_db)):
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if enc.status != EncounterStatus.approved:
        raise HTTPException(status_code=400, detail="Encounter must be approved before pushing")

    # Stub — real OpenMRS POST goes here
    enc.status = EncounterStatus.pushed
    enc.openmrs_uuid = "openmrs-encounter-mock-uuid"
    enc.updated_at = datetime.now(timezone.utc)
    db.add(AuditLog(encounter_id=enc.id, action="pushed", actor="guest",
                    detail={"openmrs_patient_uuid": body.openmrs_patient_uuid}))
    db.commit()

    return PushResponse(
        id=enc.id,
        status="pushed",
        openmrs_uuid=enc.openmrs_uuid,
        pushed_at=enc.updated_at.isoformat(),
    )
