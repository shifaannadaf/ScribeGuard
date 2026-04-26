import uuid
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.models import Encounter, Medication, Allergy, Diagnosis, AuditLog, EncounterStatus
from app.schemas.encounter import (
    EncounterListResponse, EncounterListItem, EncounterDetail,
    EncounterCreateResponse, EncounterUpdate, EncounterStatusResponse,
    MedicationOut, AllergyOut, DiagnosisOut, StatsResponse,
)

router = APIRouter(prefix="/encounters", tags=["Encounters"])


def _to_list_item(enc: Encounter) -> EncounterListItem:
    dt = enc.created_at
    snippet = (enc.transcript or "")[:120] + "…" if enc.transcript else None
    return EncounterListItem(
        id=enc.id,
        patient_name=enc.patient_name,
        patient_id=enc.patient_id,
        date=dt.strftime("%Y-%m-%d"),
        time=dt.strftime("%I:%M %p"),
        duration=enc.duration,
        status=enc.status,
        snippet=snippet,
    )


def _to_detail(enc: Encounter) -> EncounterDetail:
    return EncounterDetail(
        id=enc.id,
        patient_name=enc.patient_name,
        patient_id=enc.patient_id,
        openmrs_uuid=enc.openmrs_uuid,
        duration=enc.duration,
        status=enc.status,
        transcript=enc.transcript,
        created_at=enc.created_at,
        updated_at=enc.updated_at,
        medications=[MedicationOut.model_validate(m) for m in enc.medications],
        allergies=[AllergyOut.model_validate(a) for a in enc.allergies],
        diagnoses=[DiagnosisOut.model_validate(d) for d in enc.diagnoses],
    )


def _log(db: Session, encounter_id: str, action: str, detail: dict | None = None):
    db.add(AuditLog(encounter_id=encounter_id, action=action, actor="guest", detail=detail))


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=EncounterListResponse)
def list_encounters(
    status: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Encounter)
    if status:
        q = q.filter(Encounter.status == status)
    if search:
        q = q.filter(
            Encounter.patient_name.ilike(f"%{search}%") |
            Encounter.patient_id.ilike(f"%{search}%")
        )
    encounters = q.order_by(Encounter.created_at.desc()).all()
    return EncounterListResponse(data=[_to_list_item(e) for e in encounters])


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    today_start = datetime.combine(date.today(), datetime.min.time())
    notes_today = db.query(func.count(Encounter.id)).filter(Encounter.created_at >= today_start).scalar()
    pending     = db.query(func.count(Encounter.id)).filter(Encounter.status == EncounterStatus.pending).scalar()
    pushed      = db.query(func.count(Encounter.id)).filter(Encounter.status == EncounterStatus.pushed).scalar()
    total       = db.query(func.count(Encounter.id)).scalar()
    return StatsResponse(
        notes_today=notes_today or 0,
        pending_review=pending or 0,
        pushed_to_openmrs=pushed or 0,
        total_transcripts=total or 0,
    )


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("", response_model=EncounterCreateResponse, status_code=status.HTTP_201_CREATED)
def create_encounter(
    patient_name: str = Form(...),
    patient_id:   str = Form(...),
    db: Session = Depends(get_db),
):
    enc = Encounter(
        id=str(uuid.uuid4()),
        patient_name=patient_name,
        patient_id=patient_id,
        audio_filename=None,
        status=EncounterStatus.pending,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(enc)
    _log(db, enc.id, "created")
    db.commit()
    db.refresh(enc)
    return EncounterCreateResponse(
        id=enc.id, patient_name=enc.patient_name,
        patient_id=enc.patient_id, status=enc.status, created_at=enc.created_at,
    )


# ── Get single ────────────────────────────────────────────────────────────────

@router.get("/{encounter_id}", response_model=EncounterDetail)
def get_encounter(encounter_id: str, db: Session = Depends(get_db)):
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return _to_detail(enc)


# ── Update fields ─────────────────────────────────────────────────────────────

@router.patch("/{encounter_id}", response_model=EncounterDetail)
def update_encounter(encounter_id: str, body: EncounterUpdate, db: Session = Depends(get_db)):
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")

    if body.transcript is not None:
        enc.transcript = body.transcript

    if body.medications is not None:
        db.query(Medication).filter(Medication.encounter_id == encounter_id).delete()
        for m in body.medications:
            db.add(Medication(encounter_id=encounter_id, name=m.name, dose=m.dose,
                              route=m.route, frequency=m.frequency, start_date=m.start_date))

    if body.allergies is not None:
        db.query(Allergy).filter(Allergy.encounter_id == encounter_id).delete()
        for a in body.allergies:
            db.add(Allergy(encounter_id=encounter_id, allergen=a.allergen,
                           reaction=a.reaction, severity=a.severity))

    if body.diagnoses is not None:
        db.query(Diagnosis).filter(Diagnosis.encounter_id == encounter_id).delete()
        for d in body.diagnoses:
            db.add(Diagnosis(encounter_id=encounter_id, icd10_code=d.icd10_code,
                             description=d.description, status=d.status))

    enc.updated_at = datetime.now(timezone.utc)
    _log(db, enc.id, "edited")
    db.commit()
    db.refresh(enc)
    return _to_detail(enc)


# ── Approve ───────────────────────────────────────────────────────────────────

@router.patch("/{encounter_id}/approve", response_model=EncounterStatusResponse)
def approve_encounter(encounter_id: str, db: Session = Depends(get_db)):
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if enc.status != EncounterStatus.pending:
        raise HTTPException(status_code=400, detail="Only pending encounters can be approved")
    enc.status = EncounterStatus.approved
    enc.updated_at = datetime.now(timezone.utc)
    _log(db, enc.id, "approved")
    db.commit()
    return EncounterStatusResponse(id=enc.id, status=enc.status, updated_at=enc.updated_at)


# ── Revert ────────────────────────────────────────────────────────────────────

@router.patch("/{encounter_id}/revert", response_model=EncounterStatusResponse)
def revert_encounter(encounter_id: str, db: Session = Depends(get_db)):
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if enc.status != EncounterStatus.approved:
        raise HTTPException(status_code=400, detail="Only approved encounters can be reverted")
    enc.status = EncounterStatus.pending
    enc.updated_at = datetime.now(timezone.utc)
    _log(db, enc.id, "reverted")
    db.commit()
    return EncounterStatusResponse(id=enc.id, status=enc.status, updated_at=enc.updated_at)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{encounter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_encounter(encounter_id: str, db: Session = Depends(get_db)):
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
    db.delete(enc)
    db.commit()
