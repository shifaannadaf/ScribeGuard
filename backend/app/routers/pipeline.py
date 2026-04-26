from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Encounter, Medication, Allergy, Diagnosis, AuditLog
from app.schemas.misc import TranscribeResponse, GenerateResponse
from app.whisper_service import transcribe_audio
from app.gpt_service import generate_note, format_transcript

router = APIRouter(prefix="/encounters", tags=["Pipeline"])


def _log(db: Session, encounter_id: str, action: str):
    db.add(AuditLog(encounter_id=encounter_id, action=action, actor="guest"))


@router.post("/{encounter_id}/transcribe", response_model=TranscribeResponse)
async def transcribe(
    encounter_id: str,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")

    transcript, duration = await transcribe_audio(audio)
    formatted = await format_transcript(transcript)

    enc.transcript = formatted
    enc.duration = duration
    enc.audio_filename = audio.filename
    enc.updated_at = datetime.now(timezone.utc)
    _log(db, enc.id, "transcribed")
    db.commit()

    return TranscribeResponse(id=enc.id, transcript=enc.transcript, duration=enc.duration)


@router.post("/{encounter_id}/format", response_model=TranscribeResponse)
async def format_encounter(encounter_id: str, db: Session = Depends(get_db)):
    """Format a raw text transcript with Doctor/Patient labels."""
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")

    if not enc.transcript or not enc.transcript.strip():
        return TranscribeResponse(id=enc.id, transcript="", duration=enc.duration or "")

    enc.transcript = await format_transcript(enc.transcript)
    enc.updated_at = datetime.now(timezone.utc)
    _log(db, enc.id, "formatted")
    db.commit()

    return TranscribeResponse(id=enc.id, transcript=enc.transcript, duration=enc.duration or "")


@router.post("/{encounter_id}/generate", response_model=GenerateResponse)
async def generate(encounter_id: str, db: Session = Depends(get_db)):
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if not enc.transcript:
        raise HTTPException(status_code=400, detail="Transcribe the encounter first")

    extracted = await generate_note(enc.transcript)

    db.query(Medication).filter(Medication.encounter_id == encounter_id).delete()
    db.query(Allergy).filter(Allergy.encounter_id == encounter_id).delete()
    db.query(Diagnosis).filter(Diagnosis.encounter_id == encounter_id).delete()

    for m in extracted.get("medications", []):
        db.add(Medication(
            encounter_id=enc.id,
            name=m.get("name", ""),
            dose=m.get("dose", ""),
            route=m.get("route", ""),
            frequency=m.get("frequency", ""),
            start_date=m.get("start_date", ""),
        ))
    for a in extracted.get("allergies", []):
        db.add(Allergy(
            encounter_id=enc.id,
            allergen=a.get("allergen", ""),
            reaction=a.get("reaction", ""),
            severity=a.get("severity", ""),
        ))
    for d in extracted.get("diagnoses", []):
        db.add(Diagnosis(
            encounter_id=enc.id,
            icd10_code=d.get("icd10_code", ""),
            description=d.get("description", ""),
            status=d.get("status", ""),
        ))

    enc.updated_at = datetime.now(timezone.utc)
    _log(db, enc.id, "note_generated")
    db.commit()
    db.refresh(enc)

    return GenerateResponse(
        id=enc.id,
        medications=extracted.get("medications", []),
        allergies=extracted.get("allergies", []),
        diagnoses=extracted.get("diagnoses", []),
    )
