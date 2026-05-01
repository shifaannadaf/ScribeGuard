"""Persistence for clinical entities the extraction agent emits."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import Allergy, Condition, VitalSign, FollowUp, PatientContext


class ClinicalEntityRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Allergies ──────────────────────────────────────────────────────

    def replace_allergies(
        self,
        *,
        encounter_id: str,
        soap_note_id: Optional[int],
        allergies: list[dict],
    ) -> list[Allergy]:
        self.db.query(Allergy).filter(Allergy.encounter_id == encounter_id).delete(synchronize_session=False)
        rows: list[Allergy] = []
        for a in allergies:
            sub = (a.get("substance") or "").strip()
            if not sub:
                continue
            row = Allergy(
                encounter_id=encounter_id,
                soap_note_id=soap_note_id,
                substance=sub,
                reaction=(a.get("reaction") or None),
                severity=(a.get("severity") or None),
                category=(a.get("category") or "medication"),
                onset=(a.get("onset") or None),
                confidence=(a.get("confidence") or "medium"),
                raw_text=(a.get("raw_text") or None),
            )
            self.db.add(row)
            rows.append(row)
        self.db.flush()
        return rows

    def list_allergies(self, encounter_id: str) -> list[Allergy]:
        return self.db.query(Allergy).filter(Allergy.encounter_id == encounter_id).order_by(Allergy.id.asc()).all()

    # ── Conditions ─────────────────────────────────────────────────────

    def replace_conditions(
        self,
        *,
        encounter_id: str,
        soap_note_id: Optional[int],
        conditions: list[dict],
    ) -> list[Condition]:
        self.db.query(Condition).filter(Condition.encounter_id == encounter_id).delete(synchronize_session=False)
        rows: list[Condition] = []
        for c in conditions:
            desc = (c.get("description") or "").strip()
            if not desc:
                continue
            row = Condition(
                encounter_id=encounter_id,
                soap_note_id=soap_note_id,
                description=desc,
                icd10_code=(c.get("icd10_code") or None),
                snomed_code=(c.get("snomed_code") or None),
                clinical_status=(c.get("clinical_status") or "active"),
                verification=(c.get("verification") or "provisional"),
                onset=(c.get("onset") or None),
                note=(c.get("note") or None),
                confidence=(c.get("confidence") or "medium"),
                raw_text=(c.get("raw_text") or None),
            )
            self.db.add(row)
            rows.append(row)
        self.db.flush()
        return rows

    def list_conditions(self, encounter_id: str) -> list[Condition]:
        return self.db.query(Condition).filter(Condition.encounter_id == encounter_id).order_by(Condition.id.asc()).all()

    # ── Vital signs ────────────────────────────────────────────────────

    def replace_vital_signs(
        self,
        *,
        encounter_id: str,
        soap_note_id: Optional[int],
        vitals: list[dict],
    ) -> list[VitalSign]:
        self.db.query(VitalSign).filter(VitalSign.encounter_id == encounter_id).delete(synchronize_session=False)
        rows: list[VitalSign] = []
        for v in vitals:
            kind = (v.get("kind") or "").strip().lower()
            value = v.get("value")
            if not kind or value is None:
                continue
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
            row = VitalSign(
                encounter_id=encounter_id,
                soap_note_id=soap_note_id,
                kind=kind,
                value=value,
                unit=(v.get("unit") or None),
                measured_at=(v.get("measured_at") or None),
                confidence=(v.get("confidence") or "medium"),
                raw_text=(v.get("raw_text") or None),
            )
            self.db.add(row)
            rows.append(row)
        self.db.flush()
        return rows

    def list_vital_signs(self, encounter_id: str) -> list[VitalSign]:
        return self.db.query(VitalSign).filter(VitalSign.encounter_id == encounter_id).order_by(VitalSign.id.asc()).all()

    # ── Follow-ups ────────────────────────────────────────────────────

    def replace_follow_ups(
        self,
        *,
        encounter_id: str,
        soap_note_id: Optional[int],
        follow_ups: list[dict],
    ) -> list[FollowUp]:
        self.db.query(FollowUp).filter(FollowUp.encounter_id == encounter_id).delete(synchronize_session=False)
        rows: list[FollowUp] = []
        for f in follow_ups:
            desc = (f.get("description") or "").strip()
            if not desc:
                continue
            row = FollowUp(
                encounter_id=encounter_id,
                soap_note_id=soap_note_id,
                description=desc,
                interval=(f.get("interval") or None),
                target_date=(f.get("target_date") or None),
                with_provider=(f.get("with_provider") or None),
                confidence=(f.get("confidence") or "medium"),
            )
            self.db.add(row)
            rows.append(row)
        self.db.flush()
        return rows

    def list_follow_ups(self, encounter_id: str) -> list[FollowUp]:
        return self.db.query(FollowUp).filter(FollowUp.encounter_id == encounter_id).order_by(FollowUp.id.asc()).all()

    # ── Patient context snapshots ─────────────────────────────────────

    def save_patient_context(
        self,
        *,
        encounter_id: str,
        patient_uuid: Optional[str],
        demographics: Optional[dict[str, Any]],
        existing_medications: Optional[list[Any]],
        existing_allergies: Optional[list[Any]],
        existing_conditions: Optional[list[Any]],
        recent_observations: Optional[list[Any]],
        recent_encounters: Optional[list[Any]],
        fetch_errors: Optional[dict[str, str]],
    ) -> PatientContext:
        rec = PatientContext(
            encounter_id=encounter_id,
            patient_uuid=patient_uuid,
            patient_demographics=demographics,
            existing_medications=existing_medications,
            existing_allergies=existing_allergies,
            existing_conditions=existing_conditions,
            recent_observations=recent_observations,
            recent_encounters=recent_encounters,
            fetch_errors=fetch_errors,
        )
        self.db.add(rec)
        self.db.flush()
        return rec

    def latest_patient_context(self, encounter_id: str) -> Optional[PatientContext]:
        return (
            self.db.query(PatientContext)
            .filter(PatientContext.encounter_id == encounter_id)
            .order_by(PatientContext.fetched_at.desc())
            .first()
        )
