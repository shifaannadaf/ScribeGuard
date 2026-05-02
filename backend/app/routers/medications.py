"""Medication read endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories import MedicationRepository, EncounterRepository


router = APIRouter(prefix="/encounters", tags=["Medications"])


@router.get("/{encounter_id}/medications")
def get_medications(encounter_id: str, db: Session = Depends(get_db)):
    EncounterRepository(db).get_or_404(encounter_id)
    rows = MedicationRepository(db).for_encounter(encounter_id)
    return {
        "encounter_id": encounter_id,
        "count": len(rows),
        "medications": [
            {
                "id":          r.id,
                "name":        r.name,
                "dose":        r.dose,
                "route":       r.route,
                "frequency":   r.frequency,
                "duration":    r.duration,
                "start_date":  r.start_date,
                "indication":  r.indication,
                "confidence":  r.confidence,
                "raw_text":    r.raw_text,
                "source_section": r.source_section,
            }
            for r in rows
        ],
    }
