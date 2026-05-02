"""Encounter persistence operations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Encounter, EncounterStatus, ProcessingStage


class EncounterRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Create / Read ───────────────────────────────────────────────────

    def create(
        self,
        *,
        patient_name: str,
        patient_id: str,
        openmrs_patient_uuid: Optional[str] = None,
        encounter_id: Optional[str] = None,
    ) -> Encounter:
        enc = Encounter(
            id=encounter_id or str(uuid.uuid4()),
            patient_name=patient_name,
            patient_id=patient_id,
            openmrs_patient_uuid=openmrs_patient_uuid,
            status=EncounterStatus.pending,
            processing_stage=ProcessingStage.created,
        )
        self.db.add(enc)
        self.db.flush()
        return enc

    def get(self, encounter_id: str) -> Optional[Encounter]:
        return self.db.get(Encounter, encounter_id)

    def get_or_404(self, encounter_id: str) -> Encounter:
        enc = self.get(encounter_id)
        if not enc:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Encounter {encounter_id} not found")
        return enc

    def list(
        self,
        *,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[Encounter]:
        q = self.db.query(Encounter)
        if status:
            q = q.filter(Encounter.status == status)
        if search:
            like = f"%{search}%"
            q = q.filter(
                (Encounter.patient_name.ilike(like)) |
                (Encounter.patient_id.ilike(like))
            )
        return q.order_by(Encounter.created_at.desc()).all()

    # ── Updates ────────────────────────────────────────────────────────

    def update_audio(
        self,
        enc: Encounter,
        *,
        filename: str,
        path: str,
        size_bytes: int,
        mime: str,
    ) -> Encounter:
        enc.audio_filename   = filename
        enc.audio_path       = path
        enc.audio_size_bytes = str(size_bytes)
        enc.audio_mime       = mime
        self._touch(enc)
        return enc

    def set_processing_stage(self, enc: Encounter, stage: ProcessingStage) -> Encounter:
        enc.processing_stage = stage
        self._touch(enc)
        return enc

    def set_status(self, enc: Encounter, status: EncounterStatus) -> Encounter:
        enc.status = status
        self._touch(enc)
        return enc

    def set_error(self, enc: Encounter, message: str) -> Encounter:
        enc.last_error = message
        enc.processing_stage = ProcessingStage.failed
        enc.status = EncounterStatus.failed
        self._touch(enc)
        return enc

    def clear_error(self, enc: Encounter) -> Encounter:
        enc.last_error = None
        if enc.status == EncounterStatus.failed:
            enc.status = EncounterStatus.pending
        self._touch(enc)
        return enc

    def update_audio_duration(self, enc: Encounter, duration_seconds: float) -> Encounter:
        enc.audio_duration_sec = f"{duration_seconds:.1f}"
        # Also keep the legacy human-readable string for the existing UI.
        m, s = divmod(int(round(duration_seconds)), 60)
        enc.duration = f"{m}m {s:02d}s" if m else f"{s}s"
        self._touch(enc)
        return enc

    def delete(self, enc: Encounter) -> None:
        self.db.delete(enc)

    # ── Internal ───────────────────────────────────────────────────────

    @staticmethod
    def _touch(enc: Encounter) -> None:
        enc.updated_at = datetime.now(timezone.utc)
