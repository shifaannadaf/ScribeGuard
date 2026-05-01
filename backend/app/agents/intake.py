"""
Agent 1 — Encounter Intake Agent.

Owns the *physician audio intake workflow* end-to-end:
    - validates that an audio file is present in the agent payload
    - validates format / size / mime
    - persists the raw bytes to disk via AudioStorage
    - records audio metadata on the encounter
    - emits an audit event marking the encounter as "audio_received"

Once this agent succeeds the orchestrator can hand off to the
TranscriptionAgent. Until it succeeds, no downstream agent will run.
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents import Agent, AgentContext, AgentResult
from app.agents.audio_storage import AudioStorage
from app.agents.exceptions import AgentValidationError
from app.config import settings
from app.models import ProcessingStage


logger = logging.getLogger("scribeguard.agents.intake")


# Whitelist matches what MediaRecorder + common upload UIs emit
ALLOWED_MIME_PREFIXES = ("audio/", "video/")  # webm video container counts
MAX_BYTES = 200 * 1024 * 1024                 # 200 MB ceiling


class EncounterIntakeAgent(Agent[dict[str, Any]]):
    name = "EncounterIntakeAgent"
    version = "1.1.0"
    description = (
        "Validates a physician's audio recording, stores it durably, and "
        "records intake metadata on the encounter."
    )

    def __init__(self, audio_storage: AudioStorage | None = None):
        self.storage = audio_storage or AudioStorage(settings.AUDIO_STORAGE_DIR)
        # Lazy import — avoids pulling httpx at module import time
        from app.agents.openmrs.patient_context import OpenMRSPatientContextAgent
        self._context = OpenMRSPatientContextAgent()

    # The orchestrator passes audio bytes through `ctx.payload` since FastAPI
    # UploadFile objects can't roundtrip through the orchestrator boundary.
    def input_summary(self, ctx: AgentContext) -> dict[str, Any]:
        return {
            "encounter_id": ctx.encounter_id,
            "patient_id":   ctx.encounter.patient_id,
            "filename":     ctx.payload.get("audio_filename"),
            "mime":         ctx.payload.get("audio_mime"),
            "size_bytes":   len(ctx.payload.get("audio_bytes") or b""),
        }

    async def run(self, ctx: AgentContext) -> AgentResult[dict[str, Any]]:
        encounter = ctx.encounter
        payload = ctx.payload

        # If audio has already been ingested in a previous run, this agent
        # is idempotent — no re-store, no error.
        if not payload.get("audio_bytes"):
            if encounter.audio_path:
                ctx.encounters.set_processing_stage(encounter, ProcessingStage.audio_received)
                return AgentResult(
                    success=True,
                    output={"audio_path": encounter.audio_path},
                    summary={
                        "status": "already_ingested",
                        "audio_path": encounter.audio_path,
                        "filename": encounter.audio_filename,
                    },
                )
            raise AgentValidationError(
                "No audio bytes provided for intake (and the encounter has no prior audio)."
            )

        audio_bytes: bytes = payload["audio_bytes"]
        filename = payload.get("audio_filename") or "recording.webm"
        mime     = payload.get("audio_mime") or "audio/webm"

        # ── Validate -----------------------------------------------------
        if len(audio_bytes) == 0:
            raise AgentValidationError("Audio file is empty.")
        if len(audio_bytes) > MAX_BYTES:
            raise AgentValidationError(
                f"Audio file too large: {len(audio_bytes):,} bytes (max {MAX_BYTES:,})."
            )
        if not any(mime.startswith(p) for p in ALLOWED_MIME_PREFIXES):
            raise AgentValidationError(
                f"Unsupported audio mime type: {mime}. "
                f"Expected one of {ALLOWED_MIME_PREFIXES}."
            )

        # ── Persist ------------------------------------------------------
        path = self.storage.save(
            encounter_id=encounter.id,
            filename=filename,
            content=audio_bytes,
        )
        ctx.encounters.update_audio(
            encounter,
            filename=filename,
            path=path,
            size_bytes=len(audio_bytes),
            mime=mime,
        )
        ctx.encounters.set_processing_stage(encounter, ProcessingStage.audio_received)

        ctx.audit.append(
            encounter_id=encounter.id,
            event_type="audio.intake",
            agent_name=self.name,
            actor=ctx.actor,
            summary=f"Audio ingested ({len(audio_bytes):,} bytes, {mime})",
            payload={"filename": filename, "size_bytes": len(audio_bytes), "mime": mime},
        )
        logger.info(
            "Intake complete encounter=%s filename=%s size=%d", encounter.id, filename, len(audio_bytes)
        )

        # Best-effort: snapshot the patient's existing OpenMRS chart so the
        # physician review UI can show context. Failures here NEVER abort
        # the pipeline — the snapshot is purely informational.
        try:
            patient = self._context.resolve(
                openmrs_patient_uuid=encounter.openmrs_patient_uuid,
                local_patient_id=encounter.patient_id,
            )
            chart = self._context.fetch_chart_context(patient_uuid=patient["uuid"])
            ctx.entities.save_patient_context(
                encounter_id=encounter.id,
                patient_uuid=patient["uuid"],
                demographics=chart.get("demographics"),
                existing_medications=chart.get("existing_medications"),
                existing_allergies=chart.get("existing_allergies"),
                existing_conditions=chart.get("existing_conditions"),
                recent_observations=chart.get("recent_observations"),
                recent_encounters=chart.get("recent_encounters"),
                fetch_errors=chart.get("errors"),
            )
            if patient["uuid"] and not encounter.openmrs_patient_uuid:
                encounter.openmrs_patient_uuid = patient["uuid"]
            ctx.audit.append(
                encounter_id=encounter.id,
                event_type="patient_context.snapshot",
                agent_name=self.name,
                actor=ctx.actor,
                summary=(
                    f"Snapshot OpenMRS chart for {patient['uuid']}: "
                    f"meds={len(chart.get('existing_medications') or [])}, "
                    f"allergies={len(chart.get('existing_allergies') or [])}, "
                    f"conditions={len(chart.get('existing_conditions') or [])}"
                ),
                payload={"patient_uuid": patient["uuid"]},
            )
        except Exception as exc:  # noqa: BLE001
            ctx.audit.append(
                encounter_id=encounter.id,
                event_type="patient_context.snapshot_failed",
                agent_name=self.name,
                actor=ctx.actor,
                severity="warning",
                summary=f"Could not snapshot OpenMRS chart: {exc}",
                payload={"error": str(exc)},
            )

        return AgentResult(
            success=True,
            output={"audio_path": path, "size_bytes": len(audio_bytes)},
            summary={
                "filename": filename,
                "size_bytes": len(audio_bytes),
                "mime": mime,
                "path": path,
            },
        )
