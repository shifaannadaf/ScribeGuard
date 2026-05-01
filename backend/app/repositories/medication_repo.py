"""Medication persistence."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Medication


class MedicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def replace_for_note(
        self,
        *,
        encounter_id: str,
        soap_note_id: int,
        medications: list[dict],
    ) -> list[Medication]:
        # Remove any existing medications for this note (regeneration scenario)
        (
            self.db.query(Medication)
            .filter(Medication.soap_note_id == soap_note_id)
            .delete(synchronize_session=False)
        )
        rows: list[Medication] = []
        for m in medications:
            row = Medication(
                encounter_id=encounter_id,
                soap_note_id=soap_note_id,
                name=(m.get("name") or "").strip(),
                dose=m.get("dose") or None,
                route=m.get("route") or None,
                frequency=m.get("frequency") or None,
                duration=m.get("duration") or None,
                start_date=m.get("start_date") or None,
                indication=m.get("indication") or None,
                raw_text=m.get("raw_text") or None,
                source_section=m.get("source_section") or "plan",
                confidence=m.get("confidence") or None,
            )
            if not row.name:
                continue
            self.db.add(row)
            rows.append(row)
        self.db.flush()
        return rows

    def for_note(self, soap_note_id: int) -> list[Medication]:
        return (
            self.db.query(Medication)
            .filter(Medication.soap_note_id == soap_note_id)
            .order_by(Medication.id.asc())
            .all()
        )

    def for_encounter(self, encounter_id: str) -> list[Medication]:
        return (
            self.db.query(Medication)
            .filter(Medication.encounter_id == encounter_id)
            .order_by(Medication.id.asc())
            .all()
        )
