"""SOAP note persistence."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models import SoapNote, SoapNoteStatus, PhysicianEdit, PhysicianApproval


class SoapRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── SOAP notes ─────────────────────────────────────────────────────

    def create_version(
        self,
        *,
        encounter_id: str,
        subjective: str,
        objective: str,
        assessment: str,
        plan: str,
        raw_markdown: Optional[str],
        low_confidence_sections: Optional[list[str]],
        flags: Optional[dict],
        model: str,
        prompt_version: str,
        agent_name: str,
    ) -> SoapNote:
        # Mark all existing as superseded
        existing = (
            self.db.query(SoapNote)
            .filter(SoapNote.encounter_id == encounter_id)
            .all()
        )
        next_version = (max((n.version for n in existing), default=0) + 1)
        for n in existing:
            n.is_current = False
            if n.status not in (SoapNoteStatus.approved,):
                n.status = SoapNoteStatus.superseded

        note = SoapNote(
            encounter_id=encounter_id,
            version=next_version,
            is_current=True,
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan,
            raw_markdown=raw_markdown,
            low_confidence_sections=low_confidence_sections or [],
            flags=flags or {},
            status=SoapNoteStatus.ai_draft,
            model=model,
            prompt_version=prompt_version,
            generated_by_agent=agent_name,
        )
        self.db.add(note)
        self.db.flush()
        return note

    def current_for(self, encounter_id: str) -> Optional[SoapNote]:
        return (
            self.db.query(SoapNote)
            .filter(SoapNote.encounter_id == encounter_id, SoapNote.is_current == True)  # noqa: E712
            .one_or_none()
        )

    def update_sections(
        self,
        note: SoapNote,
        *,
        subjective: Optional[str] = None,
        objective:  Optional[str] = None,
        assessment: Optional[str] = None,
        plan:       Optional[str] = None,
    ) -> SoapNote:
        edited = False
        if subjective is not None and subjective != note.subjective:
            note.subjective = subjective
            edited = True
        if objective is not None and objective != note.objective:
            note.objective = objective
            edited = True
        if assessment is not None and assessment != note.assessment:
            note.assessment = assessment
            edited = True
        if plan is not None and plan != note.plan:
            note.plan = plan
            edited = True
        if edited and note.status == SoapNoteStatus.ai_draft:
            note.status = SoapNoteStatus.physician_edited
        return note

    def mark_approved(self, note: SoapNote) -> SoapNote:
        note.status = SoapNoteStatus.approved
        return note

    # ── Physician trail ────────────────────────────────────────────────

    def record_edit(
        self,
        *,
        encounter_id: str,
        soap_note_id: int,
        section: str,
        original: Optional[str],
        edited: Optional[str],
        actor: str = "physician",
    ) -> PhysicianEdit:
        e = PhysicianEdit(
            encounter_id=encounter_id,
            soap_note_id=soap_note_id,
            section=section,
            original_text=original,
            edited_text=edited,
            actor=actor,
        )
        self.db.add(e)
        return e

    def record_approval(
        self,
        *,
        encounter_id: str,
        soap_note_id: int,
        actor: str = "physician",
        comments: Optional[str] = None,
        edits_made: int = 0,
    ) -> PhysicianApproval:
        a = PhysicianApproval(
            encounter_id=encounter_id,
            soap_note_id=soap_note_id,
            actor=actor,
            comments=comments,
            edits_made=edits_made,
        )
        self.db.add(a)
        return a

    def count_edits(self, soap_note_id: int) -> int:
        return (
            self.db.query(PhysicianEdit)
            .filter(PhysicianEdit.soap_note_id == soap_note_id)
            .count()
        )
