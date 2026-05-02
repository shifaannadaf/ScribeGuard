"""
Pipeline orchestration endpoints.

These mirror what the auto-pipeline does, but expose individual stages so
operators / debug tools can drive the pipeline a step at a time.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories import EncounterRepository, AgentRunRepository
from app.routers._dependencies import get_orchestrator
from app.schemas.pipeline import (
    AgentRunOut,
    GenerateSoapResponse,
    PipelineStatus,
    RunPipelineResponse,
    TranscribeResponse,
)


router = APIRouter(prefix="/encounters", tags=["Pipeline"])


# ── End-to-end ──────────────────────────────────────────────────────────

@router.post("/{encounter_id}/run", response_model=RunPipelineResponse)
async def run_full_pipeline(
    encounter_id: str,
    db: Session = Depends(get_db),
    orchestrator = Depends(get_orchestrator),
):
    enc = EncounterRepository(db).get_or_404(encounter_id)
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


# ── Per-stage agents ────────────────────────────────────────────────────

@router.post("/{encounter_id}/transcribe", response_model=TranscribeResponse)
async def run_transcription(
    encounter_id: str,
    audio: UploadFile = File(default=None),
    db: Session = Depends(get_db),
    orchestrator = Depends(get_orchestrator),
):
    enc = EncounterRepository(db).get_or_404(encounter_id)
    payload = {}
    if audio is not None:
        content = await audio.read()
        payload = {
            "audio_bytes":    content,
            "audio_filename": audio.filename,
            "audio_mime":     audio.content_type or "audio/webm",
        }
        await orchestrator.run_agent("EncounterIntakeAgent", enc, actor="physician", payload=payload)

    result = await orchestrator.run_agent("TranscriptionAgent", enc, actor="physician")
    return TranscribeResponse(
        encounter_id=enc.id,
        transcript_id=int(result.summary.get("transcript_id", 0)),
        text=(result.output or {}).get("text", ""),
        duration_seconds=result.summary.get("duration_seconds"),
        quality_score=result.summary.get("quality_score"),
        quality_issues=result.summary.get("quality_issues") or [],
    )


@router.post("/{encounter_id}/generate-soap", response_model=GenerateSoapResponse)
async def run_soap_generation(
    encounter_id: str,
    db: Session = Depends(get_db),
    orchestrator = Depends(get_orchestrator),
):
    enc = EncounterRepository(db).get_or_404(encounter_id)
    result = await orchestrator.run_agent("ClinicalNoteGenerationAgent", enc, actor="physician")
    output = result.output or {}
    # After generating the note, also run the medication extraction agent so
    # the UI receives the full review-ready bundle in one round-trip.
    med_result = await orchestrator.run_agent("MedicationExtractionAgent", enc, actor="physician")
    return GenerateSoapResponse(
        encounter_id=enc.id,
        soap_note_id=int(result.summary.get("soap_note_id", 0)),
        subjective=output.get("subjective", ""),
        objective=output.get("objective", ""),
        assessment=output.get("assessment", ""),
        plan=output.get("plan", ""),
        medications_extracted=int(med_result.summary.get("count", 0)),
        low_confidence_sections=result.summary.get("low_confidence_sections") or [],
    )


@router.post("/{encounter_id}/extract-medications")
async def run_medication_extraction(
    encounter_id: str,
    db: Session = Depends(get_db),
    orchestrator = Depends(get_orchestrator),
):
    enc = EncounterRepository(db).get_or_404(encounter_id)
    result = await orchestrator.run_agent("MedicationExtractionAgent", enc, actor="physician")
    return {"encounter_id": enc.id, **result.summary}


# ── Status / inspection ────────────────────────────────────────────────

@router.get("/{encounter_id}/pipeline", response_model=PipelineStatus)
def get_pipeline_status(encounter_id: str, db: Session = Depends(get_db)):
    enc = EncounterRepository(db).get_or_404(encounter_id)
    runs = AgentRunRepository(db).for_encounter(encounter_id)
    return PipelineStatus(
        encounter_id=enc.id,
        processing_stage=enc.processing_stage.value,
        status=enc.status.value,
        last_error=enc.last_error,
        has_audio=bool(enc.audio_path),
        has_transcript=bool(enc.latest_transcript),
        has_soap_note=enc.current_soap_note is not None,
        has_approval=any(
            n.status.value == "approved" for n in enc.soap_notes
        ),
        submitted=enc.status.value == "pushed",
        agent_runs=[AgentRunOut.model_validate(r) for r in runs],
    )
