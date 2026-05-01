"""OpenMRS submission persistence."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import SubmissionRecord, SubmissionStatus


class SubmissionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_pending(
        self,
        *,
        encounter_id: str,
        soap_note_id: Optional[int],
        openmrs_patient_uuid: Optional[str],
    ) -> SubmissionRecord:
        rec = SubmissionRecord(
            encounter_id=encounter_id,
            soap_note_id=soap_note_id,
            openmrs_patient_uuid=openmrs_patient_uuid,
            status=SubmissionStatus.pending,
            attempts=0,
        )
        self.db.add(rec)
        self.db.flush()
        return rec

    def mark_in_flight(self, rec: SubmissionRecord, payload: dict[str, Any]) -> SubmissionRecord:
        rec.status = SubmissionStatus.in_flight
        rec.attempts += 1
        rec.fhir_payload = payload
        return rec

    def mark_success(
        self,
        rec: SubmissionRecord,
        *,
        encounter_uuid: Optional[str],
        observation_uuid: Optional[str] = None,
        response: Optional[dict[str, Any]] = None,
    ) -> SubmissionRecord:
        rec.status = SubmissionStatus.success
        rec.openmrs_encounter_uuid = encounter_uuid
        rec.openmrs_observation_uuid = observation_uuid
        rec.fhir_response = response
        rec.completed_at = datetime.now(timezone.utc)
        rec.last_error = None
        return rec

    def mark_verified(self, rec: SubmissionRecord) -> SubmissionRecord:
        rec.status = SubmissionStatus.verified
        rec.completed_at = datetime.now(timezone.utc)
        return rec

    def mark_failed(self, rec: SubmissionRecord, error: str) -> SubmissionRecord:
        rec.status = SubmissionStatus.failed
        rec.last_error = error
        rec.completed_at = datetime.now(timezone.utc)
        return rec

    def latest_for(self, encounter_id: str) -> Optional[SubmissionRecord]:
        return (
            self.db.query(SubmissionRecord)
            .filter(SubmissionRecord.encounter_id == encounter_id)
            .order_by(desc(SubmissionRecord.started_at))
            .first()
        )
