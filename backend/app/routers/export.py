from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Encounter

router = APIRouter(prefix="/encounters", tags=["Export"])


@router.get("/{encounter_id}/export/pdf")
def export_pdf(encounter_id: str, db: Session = Depends(get_db)):
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")

    # Stub — real PDF generation (WeasyPrint / ReportLab) goes here
    content = f"ScribeGuard Export\n\nPatient: {enc.patient_name}\nID: {enc.patient_id}\nStatus: {enc.status.value}\n\nTranscript:\n{enc.transcript or 'No transcript yet.'}"

    return Response(
        content=content.encode(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=encounter_{encounter_id}.pdf"},
    )
