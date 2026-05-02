"""
Agent 4 (rev) — Clinical Entity Extraction Agent.

Replaces the previous medication-only extractor. Classifies the SOAP note
into FHIR-aligned buckets:

    medications | allergies | conditions | vital_signs | follow_ups

Each bucket is persisted into its own table by the appropriate repository,
and the OpenMRS Integration Agent writes each bucket into the correct FHIR
R4 resource on submission.
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents import Agent, AgentContext, AgentResult
from app.agents.exceptions import AgentExecutionError, AgentValidationError
from app.agents.prompts.clinical_extraction import (
    PROMPT_VERSION,
    CLINICAL_ENTITY_SYSTEM_PROMPT,
    CLINICAL_ENTITY_USER_TEMPLATE,
)
from app.clients import ai_client
from app.config import settings


logger = logging.getLogger("scribeguard.agents.clinical_extraction")


class ClinicalEntityExtractionAgent(Agent[dict[str, Any]]):
    name = "ClinicalEntityExtractionAgent"
    version = "1.0.0"
    description = (
        "Classifies the SOAP note + transcript into FHIR-aligned clinical "
        "entities (medications, allergies, conditions, vital signs, "
        "follow-ups) ready for OpenMRS write-back."
    )

    def input_summary(self, ctx: AgentContext) -> dict[str, Any]:
        note = ctx.soap_notes.current_for(ctx.encounter_id)
        return {
            "encounter_id": ctx.encounter_id,
            "soap_note_id": note.id if note else None,
            "model": settings.MEDICATION_MODEL,
            "prompt_version": PROMPT_VERSION,
        }

    async def run(self, ctx: AgentContext) -> AgentResult[dict[str, Any]]:
        note = ctx.soap_notes.current_for(ctx.encounter_id)
        if not note:
            raise AgentValidationError("Cannot extract clinical entities — no SOAP note available.")

        transcript = ctx.transcripts.latest_for(ctx.encounter_id)
        transcript_text = (
            (transcript.formatted_text or transcript.raw_text) if transcript else ""
        ) or ""

        try:
            data = await ai_client.chat_json(
                system=CLINICAL_ENTITY_SYSTEM_PROMPT,
                user=CLINICAL_ENTITY_USER_TEMPLATE.format(
                    subjective=note.subjective or "",
                    objective=note.objective or "",
                    assessment=note.assessment or "",
                    plan=note.plan or "",
                    transcript=transcript_text[:6000],
                ),
                model=settings.MEDICATION_MODEL,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Clinical entity extraction failed for encounter %s", ctx.encounter_id)
            raise AgentExecutionError(f"Clinical entity extraction failed: {exc}") from exc

        meds       = self._normalize_meds(data.get("medications") or [])
        allergies  = self._listify(data.get("allergies"))
        conditions = self._listify(data.get("conditions"))
        vitals     = self._normalize_vitals(data.get("vital_signs") or [])
        followups  = self._listify(data.get("follow_ups"))

        med_rows = ctx.medications.replace_for_note(
            encounter_id=ctx.encounter_id, soap_note_id=note.id, medications=meds,
        )
        allergy_rows   = ctx.entities.replace_allergies(encounter_id=ctx.encounter_id, soap_note_id=note.id, allergies=allergies)
        condition_rows = ctx.entities.replace_conditions(encounter_id=ctx.encounter_id, soap_note_id=note.id, conditions=conditions)
        vital_rows     = ctx.entities.replace_vital_signs(encounter_id=ctx.encounter_id, soap_note_id=note.id, vitals=vitals)
        followup_rows  = ctx.entities.replace_follow_ups(encounter_id=ctx.encounter_id, soap_note_id=note.id, follow_ups=followups)

        ctx.audit.append(
            encounter_id=ctx.encounter_id,
            event_type="clinical_entities.extracted",
            agent_name=self.name,
            actor=ctx.actor,
            summary=(
                f"Extracted {len(med_rows)} med(s), {len(allergy_rows)} allergy(ies), "
                f"{len(condition_rows)} condition(s), {len(vital_rows)} vital(s), "
                f"{len(followup_rows)} follow-up(s)"
            ),
            payload={
                "soap_note_id":   note.id,
                "medications":    [r.name for r in med_rows],
                "allergies":      [r.substance for r in allergy_rows],
                "conditions":     [r.description for r in condition_rows],
                "vitals":         [{"kind": r.kind, "value": r.value, "unit": r.unit} for r in vital_rows],
                "follow_ups":     [r.description for r in followup_rows],
                "prompt_version": PROMPT_VERSION,
            },
        )

        return AgentResult(
            success=True,
            output={
                "medications": [m.name for m in med_rows],
                "allergies":   [a.substance for a in allergy_rows],
                "conditions":  [c.description for c in condition_rows],
                "vitals":      [{"kind": v.kind, "value": v.value, "unit": v.unit} for v in vital_rows],
                "follow_ups":  [f.description for f in followup_rows],
            },
            summary={
                "soap_note_id":         note.id,
                "medications_count":    len(med_rows),
                "allergies_count":      len(allergy_rows),
                "conditions_count":     len(condition_rows),
                "vital_signs_count":    len(vital_rows),
                "follow_ups_count":     len(followup_rows),
                # Backwards-compat key for the orchestrator's legacy field
                "count":                len(med_rows),
                "model":                settings.MEDICATION_MODEL,
                "prompt_version":       PROMPT_VERSION,
            },
        )

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _listify(v):
        return v if isinstance(v, list) else []

    @staticmethod
    def _normalize_meds(items: list) -> list[dict]:
        out: list[dict] = []
        for m in items:
            if not isinstance(m, dict):
                continue
            name = (m.get("name") or "").strip()
            if not name:
                continue
            out.append({
                "name":           name,
                "dose":           (m.get("dose") or None),
                "route":          (m.get("route") or None),
                "frequency":      (m.get("frequency") or None),
                "duration":       (m.get("duration") or None),
                "indication":     (m.get("indication") or None),
                "raw_text":       (m.get("raw_text") or ""),
                "confidence":     (m.get("confidence") or "medium"),
                "source_section": (m.get("source_section") or "plan"),
            })
        return out

    @staticmethod
    def _normalize_vitals(items: list) -> list[dict]:
        canonical = {
            "height": "height", "weight": "weight",
            "temperature": "temperature", "temp": "temperature",
            "respiratory_rate": "respiratory_rate", "rr": "respiratory_rate",
            "spo2": "spo2", "saturation": "spo2", "oxygen_saturation": "spo2",
            "hr": "hr", "heart_rate": "hr", "pulse": "hr",
            "systolic_bp": "systolic_bp", "sbp": "systolic_bp",
            "diastolic_bp": "diastolic_bp", "dbp": "diastolic_bp",
        }
        out: list[dict] = []
        for v in items:
            if not isinstance(v, dict):
                continue
            kind = (v.get("kind") or "").strip().lower().replace(" ", "_")
            kind = canonical.get(kind, kind)
            value = v.get("value")
            try:
                value_f = float(value)
            except (TypeError, ValueError):
                continue
            if not kind:
                continue
            out.append({
                "kind":         kind,
                "value":        value_f,
                "unit":         (v.get("unit") or None),
                "measured_at":  (v.get("measured_at") or None),
                "raw_text":     (v.get("raw_text") or None),
                "confidence":   (v.get("confidence") or "medium"),
            })
        return out
