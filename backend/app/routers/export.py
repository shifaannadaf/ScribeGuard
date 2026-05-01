"""Encounter export — returns the SOAP note + transcript as plain text/markdown."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories import (
    EncounterRepository,
    MedicationRepository,
    SoapRepository,
    TranscriptRepository,
)


router = APIRouter(prefix="/encounters", tags=["Export"])


@router.get("/{encounter_id}/export/markdown")
def export_markdown(encounter_id: str, db: Session = Depends(get_db)):
    enc = EncounterRepository(db).get_or_404(encounter_id)
    transcript = TranscriptRepository(db).latest_for(encounter_id)
    note = SoapRepository(db).current_for(encounter_id)
    meds = MedicationRepository(db).for_encounter(encounter_id)

    lines: list[str] = []
    lines.append(f"# ScribeGuard Encounter Export")
    lines.append("")
    lines.append(f"- **Patient:** {enc.patient_name} ({enc.patient_id})")
    lines.append(f"- **Encounter ID:** {enc.id}")
    lines.append(f"- **Created:** {enc.created_at.isoformat()}")
    lines.append(f"- **Status:** {enc.status.value}")
    lines.append(f"- **Pipeline stage:** {enc.processing_stage.value}")
    lines.append("")
    if note:
        lines.append(f"## SOAP Note (v{note.version}, {note.status.value})")
        lines.append("")
        lines.append("### Subjective")
        lines.append(note.subjective or "_(empty)_")
        lines.append("")
        lines.append("### Objective")
        lines.append(note.objective or "_(empty)_")
        lines.append("")
        lines.append("### Assessment")
        lines.append(note.assessment or "_(empty)_")
        lines.append("")
        lines.append("### Plan")
        lines.append(note.plan or "_(empty)_")
        lines.append("")
    else:
        lines.append("_(No SOAP note generated yet.)_")
        lines.append("")
    if meds:
        lines.append("## Medications")
        for m in meds:
            parts = [m.name]
            for label, val in (("dose", m.dose), ("route", m.route), ("freq", m.frequency), ("duration", m.duration)):
                if val:
                    parts.append(f"{label}={val}")
            lines.append(f"- {' '.join(parts)}")
        lines.append("")
    if transcript:
        lines.append("## Transcript")
        lines.append("```")
        lines.append(transcript.formatted_text or transcript.raw_text or "")
        lines.append("```")
    body = "\n".join(lines)
    return Response(
        content=body,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=encounter_{encounter_id}.md"},
    )
