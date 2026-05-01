"""
Encounter CRUD + intake endpoints.

The intake endpoint here is the single physician-facing audio upload — it
delegates to the EncounterIntakeAgent and (optionally) auto-runs the rest of
the pipeline. Thin physician dashboards typically call `/encounters/{id}/run`
after intake, but the convenience flag keeps the demo flow one click.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Encounter, EncounterStatus, ProcessingStage, AuditEvent
from app.repositories import EncounterRepository
from app.routers._dependencies import get_orchestrator
from app.schemas.encounter import (
    EncounterCreate,
    EncounterCreated,
    EncounterDetail,
    EncounterListItem,
    EncounterListResponse,
    StatsResponse,
)
from app.schemas.pipeline import RunPipelineResponse


router = APIRouter(prefix="/encounters", tags=["Encounters"])


# ── List / Stats ────────────────────────────────────────────────────────

@router.get("", response_model=EncounterListResponse)
def list_encounters(
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    repo = EncounterRepository(db)
    encounters = repo.list(status=status, search=search)
    return EncounterListResponse(data=[_to_list_item(e) for e in encounters])


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    today_start = datetime.combine(date.today(), datetime.min.time())
    notes_today = db.query(func.count(Encounter.id)).filter(Encounter.created_at >= today_start).scalar() or 0
    pending     = db.query(func.count(Encounter.id)).filter(Encounter.status == EncounterStatus.pending).scalar() or 0
    pushed      = db.query(func.count(Encounter.id)).filter(Encounter.status == EncounterStatus.pushed).scalar() or 0
    failed      = db.query(func.count(Encounter.id)).filter(Encounter.status == EncounterStatus.failed).scalar() or 0
    total       = db.query(func.count(Encounter.id)).scalar() or 0
    return StatsResponse(
        notes_today=notes_today,
        pending_review=pending,
        pushed_to_openmrs=pushed,
        failed=failed,
        total_encounters=total,
    )


# ── Create / Detail / Delete ────────────────────────────────────────────

@router.post("", response_model=EncounterCreated, status_code=status.HTTP_201_CREATED)
def create_encounter(
    patient_name: str = Form(...),
    patient_id:   str = Form(...),
    openmrs_patient_uuid: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    repo = EncounterRepository(db)
    enc = repo.create(
        patient_name=patient_name,
        patient_id=patient_id,
        openmrs_patient_uuid=openmrs_patient_uuid,
    )
    db.add(AuditEvent(
        encounter_id=enc.id,
        event_type="encounter.created",
        agent_name=None,
        actor="physician",
        summary=f"Encounter created for {patient_name} ({patient_id})",
        payload={"patient_name": patient_name, "patient_id": patient_id},
    ))
    db.commit()
    db.refresh(enc)
    return EncounterCreated(
        id=enc.id,
        patient_name=enc.patient_name,
        patient_id=enc.patient_id,
        openmrs_patient_uuid=enc.openmrs_patient_uuid,
        status=enc.status,
        processing_stage=enc.processing_stage,
        created_at=enc.created_at,
    )


@router.post("/json", response_model=EncounterCreated, status_code=status.HTTP_201_CREATED)
def create_encounter_json(body: EncounterCreate, db: Session = Depends(get_db)):
    """JSON body alternative to the form-based create endpoint."""
    repo = EncounterRepository(db)
    enc = repo.create(
        patient_name=body.patient_name,
        patient_id=body.patient_id,
        openmrs_patient_uuid=body.openmrs_patient_uuid,
    )
    db.add(AuditEvent(
        encounter_id=enc.id,
        event_type="encounter.created",
        actor="physician",
        summary=f"Encounter created for {body.patient_name} ({body.patient_id})",
    ))
    db.commit()
    db.refresh(enc)
    return EncounterCreated(
        id=enc.id, patient_name=enc.patient_name, patient_id=enc.patient_id,
        openmrs_patient_uuid=enc.openmrs_patient_uuid,
        status=enc.status, processing_stage=enc.processing_stage,
        created_at=enc.created_at,
    )


@router.get("/{encounter_id}", response_model=EncounterDetail)
def get_encounter(encounter_id: str, db: Session = Depends(get_db)):
    enc = EncounterRepository(db).get_or_404(encounter_id)
    return _to_detail(enc)


@router.delete("/{encounter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_encounter(encounter_id: str, db: Session = Depends(get_db)):
    repo = EncounterRepository(db)
    enc = repo.get_or_404(encounter_id)
    repo.delete(enc)
    db.commit()


# ── Intake (audio upload) ──────────────────────────────────────────────

@router.post("/{encounter_id}/intake", response_model=RunPipelineResponse)
async def intake_audio(
    encounter_id: str,
    audio: UploadFile = File(...),
    auto_run: bool = True,
    db: Session = Depends(get_db),
    orchestrator = Depends(get_orchestrator),
):
    """Accepts an audio upload and (by default) runs the full agent pipeline.

    The IntakeAgent validates and stores the audio, then if `auto_run=true`
    the orchestrator drives Transcription → SOAP → Medication extraction.
    Physician review and OpenMRS submission remain explicit downstream
    actions.
    """
    enc = EncounterRepository(db).get_or_404(encounter_id)
    content = await audio.read()
    payload = {
        "audio_bytes":    content,
        "audio_filename": audio.filename,
        "audio_mime":     audio.content_type or "audio/webm",
    }

    # Step 1: intake
    await orchestrator.run_agent(
        "EncounterIntakeAgent", enc, actor="physician", payload=payload,
    )

    if not auto_run:
        return RunPipelineResponse(
            encounter_id=enc.id,
            final_stage=enc.processing_stage.value,
            status=enc.status.value,
            duration_ms=0.0,
            errors=[],
        )

    outcome = await orchestrator.run_pipeline(enc, actor="physician")
    return RunPipelineResponse(
        encounter_id=enc.id,
        final_stage=outcome.final_stage.value,
        status=enc.status.value,
        transcript_id=outcome.transcript_id,
        soap_note_id=outcome.soap_note_id,
        medications_extracted=outcome.medications_extracted,
        duration_ms=outcome.duration_ms,
        errors=outcome.errors,
    )


# ── Helpers ────────────────────────────────────────────────────────────

def _to_list_item(enc: Encounter) -> EncounterListItem:
    snippet = None
    transcript = enc.latest_transcript
    if transcript:
        text = transcript.formatted_text or transcript.raw_text or ""
        snippet = (text[:160] + "…") if len(text) > 160 else text
    note = enc.current_soap_note
    return EncounterListItem(
        id=enc.id,
        patient_name=enc.patient_name,
        patient_id=enc.patient_id,
        date=enc.created_at.strftime("%Y-%m-%d"),
        time=enc.created_at.strftime("%I:%M %p"),
        duration=enc.duration,
        status=enc.status,
        processing_stage=enc.processing_stage,
        snippet=snippet,
        has_soap_note=note is not None,
        medication_count=len(enc.medications),
        submitted=enc.status == EncounterStatus.pushed,
    )


def _to_detail(enc: Encounter) -> EncounterDetail:
    transcript = enc.latest_transcript
    note = enc.current_soap_note
    submission = enc.latest_submission

    transcript_payload = None
    if transcript:
        transcript_payload = {
            "id":               transcript.id,
            "raw_text":         transcript.raw_text,
            "formatted_text":   transcript.formatted_text,
            "duration_seconds": transcript.duration_seconds,
            "model":            transcript.model,
            "quality_score":    transcript.quality_score,
            "quality_issues":   transcript.quality_issues,
            "word_count":       transcript.word_count,
            "created_at":       transcript.created_at,
        }

    note_payload = None
    if note:
        note_payload = {
            "id":         note.id,
            "version":    note.version,
            "is_current": note.is_current,
            "subjective": note.subjective,
            "objective":  note.objective,
            "assessment": note.assessment,
            "plan":       note.plan,
            "status":     note.status.value if hasattr(note.status, "value") else str(note.status),
            "low_confidence_sections": note.low_confidence_sections or [],
            "flags":      note.flags or {},
            "model":      note.model,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
        }

    sub_payload = None
    if submission:
        sub_payload = {
            "id":                       submission.id,
            "status":                   submission.status.value if hasattr(submission.status, "value") else str(submission.status),
            "attempts":                 submission.attempts,
            "openmrs_encounter_uuid":   submission.openmrs_encounter_uuid,
            "openmrs_observation_uuid": submission.openmrs_observation_uuid,
            "last_error":               submission.last_error,
            "started_at":               submission.started_at,
            "completed_at":             submission.completed_at,
        }

    medications_payload = [
        {
            "id":          m.id,
            "name":        m.name,
            "dose":        m.dose,
            "route":       m.route,
            "frequency":   m.frequency,
            "duration":    m.duration,
            "start_date":  m.start_date,
            "indication":  m.indication,
            "raw_text":    m.raw_text,
            "confidence":  m.confidence,
        }
        for m in enc.medications
    ]

    allergies_payload = [
        {
            "id":          a.id,
            "substance":   a.substance,
            "reaction":    a.reaction,
            "severity":    a.severity,
            "category":    a.category,
            "onset":       a.onset,
            "confidence":  a.confidence,
            "raw_text":    a.raw_text,
            "openmrs_resource_uuid": a.openmrs_resource_uuid,
        }
        for a in enc.allergies
    ]
    conditions_payload = [
        {
            "id":              c.id,
            "description":     c.description,
            "icd10_code":      c.icd10_code,
            "snomed_code":     c.snomed_code,
            "clinical_status": c.clinical_status,
            "verification":    c.verification,
            "onset":           c.onset,
            "note":            c.note,
            "confidence":      c.confidence,
            "raw_text":        c.raw_text,
            "openmrs_resource_uuid": c.openmrs_resource_uuid,
        }
        for c in enc.conditions
    ]
    vitals_payload = [
        {
            "id":          v.id,
            "kind":        v.kind,
            "value":       v.value,
            "unit":        v.unit,
            "measured_at": v.measured_at,
            "confidence":  v.confidence,
            "raw_text":    v.raw_text,
            "openmrs_resource_uuid": v.openmrs_resource_uuid,
        }
        for v in enc.vital_signs
    ]
    followups_payload = [
        {
            "id":            f.id,
            "description":   f.description,
            "interval":      f.interval,
            "target_date":   f.target_date,
            "with_provider": f.with_provider,
            "confidence":    f.confidence,
        }
        for f in enc.follow_ups
    ]

    pc_payload = None
    pc = enc.latest_patient_context
    if pc:
        pc_payload = {
            "id":                  pc.id,
            "fetched_at":          pc.fetched_at,
            "patient_uuid":        pc.patient_uuid,
            "patient_demographics": pc.patient_demographics,
            "existing_medications": pc.existing_medications,
            "existing_allergies":   pc.existing_allergies,
            "existing_conditions":  pc.existing_conditions,
            "recent_observations":  pc.recent_observations,
            "recent_encounters":    pc.recent_encounters,
            "fetch_errors":         pc.fetch_errors,
        }

    return EncounterDetail(
        id=enc.id,
        patient_name=enc.patient_name,
        patient_id=enc.patient_id,
        openmrs_patient_uuid=enc.openmrs_patient_uuid,
        status=enc.status,
        processing_stage=enc.processing_stage,
        last_error=enc.last_error,
        duration=enc.duration,
        audio_filename=enc.audio_filename,
        audio_duration_sec=enc.audio_duration_sec,
        created_at=enc.created_at,
        updated_at=enc.updated_at,
        transcript=transcript_payload,
        soap_note=note_payload,
        medications=medications_payload,
        allergies=allergies_payload,
        conditions=conditions_payload,
        vital_signs=vitals_payload,
        follow_ups=followups_payload,
        patient_context=pc_payload,
        submission=sub_payload,
    )
