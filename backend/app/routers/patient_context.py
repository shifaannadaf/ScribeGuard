"""
Patient-context endpoints — reads (and optionally refreshes) the latest
OpenMRS chart snapshot for an encounter.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.openmrs.patient_context import OpenMRSPatientContextAgent
from app.db.database import get_db
from app.repositories import ClinicalEntityRepository, EncounterRepository


router = APIRouter(prefix="/encounters", tags=["Patient Context"])


@router.get("/{encounter_id}/patient-context")
def get_patient_context(encounter_id: str, db: Session = Depends(get_db)):
    EncounterRepository(db).get_or_404(encounter_id)
    pc = ClinicalEntityRepository(db).latest_patient_context(encounter_id)
    if not pc:
        return {"encounter_id": encounter_id, "context": None}
    return {
        "encounter_id": encounter_id,
        "context": {
            "id":                   pc.id,
            "fetched_at":           pc.fetched_at,
            "patient_uuid":         pc.patient_uuid,
            "demographics":         pc.patient_demographics,
            "existing_medications": pc.existing_medications,
            "existing_allergies":   pc.existing_allergies,
            "existing_conditions":  pc.existing_conditions,
            "recent_observations":  pc.recent_observations,
            "recent_encounters":    pc.recent_encounters,
            "fetch_errors":         pc.fetch_errors,
        },
    }


@router.post("/{encounter_id}/patient-context/refresh")
def refresh_patient_context(encounter_id: str, db: Session = Depends(get_db)):
    enc = EncounterRepository(db).get_or_404(encounter_id)
    agent = OpenMRSPatientContextAgent()
    try:
        patient = agent.resolve(
            openmrs_patient_uuid=enc.openmrs_patient_uuid,
            local_patient_id=enc.patient_id,
        )
        chart = agent.fetch_chart_context(patient_uuid=patient["uuid"])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"OpenMRS read failed: {exc}")

    rec = ClinicalEntityRepository(db).save_patient_context(
        encounter_id=enc.id,
        patient_uuid=patient["uuid"],
        demographics=chart.get("demographics"),
        existing_medications=chart.get("existing_medications"),
        existing_allergies=chart.get("existing_allergies"),
        existing_conditions=chart.get("existing_conditions"),
        recent_observations=chart.get("recent_observations"),
        recent_encounters=chart.get("recent_encounters"),
        fetch_errors=chart.get("errors"),
    )
    if patient["uuid"] and not enc.openmrs_patient_uuid:
        enc.openmrs_patient_uuid = patient["uuid"]
    db.commit()
    return {"encounter_id": enc.id, "snapshot_id": rec.id, "patient_uuid": patient["uuid"]}
