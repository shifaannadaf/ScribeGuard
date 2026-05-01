"""
Agent 5 — Physician Review Agent.

Owns the human-in-the-loop approval workflow:

    - exposes the AI-generated SOAP note as "AI-Generated Pending Review"
    - records every physician edit (per section, before/after) for audit
    - records explicit physician approvals
    - guarantees no AI output is committed without explicit approval

The agent is invoked by the routes (not by the auto-pipeline) — see
app/routers/physician_review.py. The orchestrator still wraps each call so
it gets recorded as a regular AgentRun.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.agents import Agent, AgentContext, AgentResult
from app.agents.exceptions import AgentValidationError
from app.models import EncounterStatus, ProcessingStage, SoapNoteStatus


logger = logging.getLogger("scribeguard.agents.physician_review")


class PhysicianReviewAgent(Agent[dict[str, Any]]):
    name = "PhysicianReviewAgent"
    version = "1.1.0"
    description = (
        "Manages the physician-in-the-loop SOAP review, edit, and approval "
        "workflow. No AI output is committed without explicit physician approval."
    )

    def input_summary(self, ctx: AgentContext) -> dict[str, Any]:
        return {
            "encounter_id": ctx.encounter_id,
            "action":       ctx.payload.get("action"),
            "actor":        ctx.actor,
        }

    async def run(self, ctx: AgentContext) -> AgentResult[dict[str, Any]]:
        action = ctx.payload.get("action")
        if action == "open_review":
            return self._open_review(ctx)
        if action == "edit":
            return self._edit(ctx)
        if action == "approve":
            return self._approve(ctx)
        if action == "revert":
            return self._revert(ctx)
        raise AgentValidationError(
            f"Unknown PhysicianReviewAgent action: {action!r}. "
            f"Expected one of: open_review, edit, approve, revert."
        )

    # ── Actions ────────────────────────────────────────────────────────

    def _open_review(self, ctx: AgentContext) -> AgentResult[dict[str, Any]]:
        note = ctx.soap_notes.current_for(ctx.encounter_id)
        if not note:
            raise AgentValidationError("No SOAP draft available to review.")
        ctx.encounters.set_processing_stage(ctx.encounter, ProcessingStage.in_review)
        ctx.audit.append(
            encounter_id=ctx.encounter_id,
            event_type="review.opened",
            agent_name=self.name,
            actor=ctx.actor,
            summary=f"Physician opened review for SOAP v{note.version}",
            payload={"soap_note_id": note.id},
        )
        return AgentResult(
            success=True,
            output={"soap_note_id": note.id},
            summary={"soap_note_id": note.id, "version": note.version},
        )

    def _edit(self, ctx: AgentContext) -> AgentResult[dict[str, Any]]:
        note = ctx.soap_notes.current_for(ctx.encounter_id)
        if not note:
            raise AgentValidationError("No SOAP draft available to edit.")
        if note.status == SoapNoteStatus.approved:
            raise AgentValidationError(
                "SOAP note is already approved — revert before editing."
            )

        sections: dict[str, Optional[str]] = ctx.payload.get("sections") or {}
        edits_made = 0
        for section in ("subjective", "objective", "assessment", "plan"):
            new_text = sections.get(section)
            if new_text is None:
                continue
            original = getattr(note, section)
            if new_text != original:
                ctx.soap_notes.record_edit(
                    encounter_id=ctx.encounter_id,
                    soap_note_id=note.id,
                    section=section,
                    original=original,
                    edited=new_text,
                    actor=ctx.actor,
                )
                edits_made += 1

        ctx.soap_notes.update_sections(
            note,
            subjective=sections.get("subjective"),
            objective=sections.get("objective"),
            assessment=sections.get("assessment"),
            plan=sections.get("plan"),
        )

        # Replace medications if the physician overrode them
        med_overrides = ctx.payload.get("medications")
        if isinstance(med_overrides, list):
            ctx.medications.replace_for_note(
                encounter_id=ctx.encounter_id,
                soap_note_id=note.id,
                medications=[
                    {**m, "source_section": "physician_override", "confidence": "high"}
                    for m in med_overrides
                ],
            )
            edits_made += 1

        ctx.encounters.set_processing_stage(ctx.encounter, ProcessingStage.in_review)
        ctx.audit.append(
            encounter_id=ctx.encounter_id,
            event_type="review.edited",
            agent_name=self.name,
            actor=ctx.actor,
            summary=f"Physician made {edits_made} edit(s) on SOAP v{note.version}",
            payload={"soap_note_id": note.id, "edits": edits_made},
        )

        return AgentResult(
            success=True,
            output={"soap_note_id": note.id, "edits_made": edits_made},
            summary={"soap_note_id": note.id, "edits_made": edits_made, "version": note.version},
        )

    def _approve(self, ctx: AgentContext) -> AgentResult[dict[str, Any]]:
        note = ctx.soap_notes.current_for(ctx.encounter_id)
        if not note:
            raise AgentValidationError("No SOAP draft to approve.")
        if note.status == SoapNoteStatus.approved:
            raise AgentValidationError("SOAP note is already approved.")

        ctx.soap_notes.mark_approved(note)
        edits_count = ctx.soap_notes.count_edits(note.id)
        ctx.soap_notes.record_approval(
            encounter_id=ctx.encounter_id,
            soap_note_id=note.id,
            actor=ctx.actor,
            comments=ctx.payload.get("comments"),
            edits_made=edits_count,
        )
        ctx.encounters.set_processing_stage(ctx.encounter, ProcessingStage.approved)
        ctx.encounters.set_status(ctx.encounter, EncounterStatus.approved)

        ctx.audit.append(
            encounter_id=ctx.encounter_id,
            event_type="review.approved",
            agent_name=self.name,
            actor=ctx.actor,
            summary=f"Physician approved SOAP v{note.version} after {edits_count} edit(s)",
            payload={"soap_note_id": note.id, "edits_made": edits_count},
        )

        return AgentResult(
            success=True,
            output={
                "soap_note_id": note.id,
                "approved_at":  datetime.now(timezone.utc).isoformat(),
                "edits_made":   edits_count,
            },
            summary={
                "soap_note_id": note.id,
                "edits_made":   edits_count,
                "version":      note.version,
                "actor":        ctx.actor,
            },
        )

    def _revert(self, ctx: AgentContext) -> AgentResult[dict[str, Any]]:
        note = ctx.soap_notes.current_for(ctx.encounter_id)
        if not note or note.status != SoapNoteStatus.approved:
            raise AgentValidationError("Only an approved SOAP note can be reverted.")
        note.status = SoapNoteStatus.physician_edited
        ctx.encounters.set_status(ctx.encounter, EncounterStatus.pending)
        ctx.encounters.set_processing_stage(ctx.encounter, ProcessingStage.in_review)
        ctx.audit.append(
            encounter_id=ctx.encounter_id,
            event_type="review.reverted",
            agent_name=self.name,
            actor=ctx.actor,
            summary=f"Approval reverted on SOAP v{note.version}",
            payload={"soap_note_id": note.id},
        )
        return AgentResult(success=True, summary={"soap_note_id": note.id})
