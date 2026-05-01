"""SOAP-note read endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories import EncounterRepository, SoapRepository


router = APIRouter(prefix="/encounters", tags=["SOAP Note"])


@router.get("/{encounter_id}/soap")
def get_current_soap(encounter_id: str, db: Session = Depends(get_db)):
    EncounterRepository(db).get_or_404(encounter_id)
    note = SoapRepository(db).current_for(encounter_id)
    if not note:
        raise HTTPException(status_code=404, detail="No SOAP note generated yet")
    return {
        "id":                       note.id,
        "encounter_id":             encounter_id,
        "version":                  note.version,
        "is_current":               note.is_current,
        "status":                   note.status.value,
        "subjective":               note.subjective,
        "objective":                note.objective,
        "assessment":               note.assessment,
        "plan":                     note.plan,
        "raw_markdown":             note.raw_markdown,
        "low_confidence_sections":  note.low_confidence_sections or [],
        "flags":                    note.flags or {},
        "model":                    note.model,
        "prompt_version":           note.prompt_version,
        "generated_by_agent":       note.generated_by_agent,
        "created_at":               note.created_at,
        "updated_at":               note.updated_at,
    }
