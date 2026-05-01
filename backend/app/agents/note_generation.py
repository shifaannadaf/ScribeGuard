"""
Agent 3 — Clinical Note Generation Agent.

Consumes the Transcript artifact and produces a structured SOAP note
(Subjective / Objective / Assessment / Plan) using a GPT-4 family model
under an engineered, version-pinned system prompt. The agent flags
sections it considers low-confidence so the physician review UI can
prompt the human to look harder.
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents import Agent, AgentContext, AgentResult
from app.agents.exceptions import AgentExecutionError, AgentValidationError
from app.agents.prompts.soap_generation import (
    PROMPT_VERSION,
    SOAP_SYSTEM_PROMPT,
    SOAP_USER_TEMPLATE,
)
from app.clients import ai_client
from app.config import settings


logger = logging.getLogger("scribeguard.agents.note_generation")


class ClinicalNoteGenerationAgent(Agent[dict[str, Any]]):
    name = "ClinicalNoteGenerationAgent"
    version = "1.2.0"
    description = (
        "Generates a structured SOAP note (Subjective/Objective/Assessment/Plan) "
        "from the encounter transcript and marks low-confidence sections."
    )

    def input_summary(self, ctx: AgentContext) -> dict[str, Any]:
        t = ctx.transcripts.latest_for(ctx.encounter_id)
        return {
            "encounter_id": ctx.encounter_id,
            "transcript_id": t.id if t else None,
            "transcript_chars": len((t.formatted_text or t.raw_text) if t else ""),
            "model": settings.SOAP_MODEL,
            "prompt_version": PROMPT_VERSION,
        }

    async def run(self, ctx: AgentContext) -> AgentResult[dict[str, Any]]:
        transcript = ctx.transcripts.latest_for(ctx.encounter_id)
        if not transcript:
            raise AgentValidationError("Cannot generate SOAP note — no transcript available.")

        body = (transcript.formatted_text or transcript.raw_text or "").strip()
        if len(body) < 10:
            raise AgentValidationError("Transcript is too short to generate a meaningful note.")

        try:
            data = await ai_client.chat_json(
                system=SOAP_SYSTEM_PROMPT,
                user=SOAP_USER_TEMPLATE.format(transcript=body),
                model=settings.SOAP_MODEL,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("SOAP generation failed for encounter %s", ctx.encounter_id)
            raise AgentExecutionError(f"SOAP generation failed: {exc}") from exc

        subjective = (data.get("subjective") or "").strip()
        objective  = (data.get("objective")  or "").strip()
        assessment = (data.get("assessment") or "").strip()
        plan       = (data.get("plan")       or "").strip()

        # Defensive: ensure at least one of S/O/A/P is non-empty
        if not any([subjective, objective, assessment, plan]):
            raise AgentExecutionError("Model returned an empty SOAP note.")

        low_conf = data.get("low_confidence_sections") or []
        if not isinstance(low_conf, list):
            low_conf = []
        flags = data.get("flags") or {}
        if not isinstance(flags, dict):
            flags = {}

        raw_md = self._render_markdown(subjective, objective, assessment, plan)

        soap_note = ctx.soap_notes.create_version(
            encounter_id=ctx.encounter_id,
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan,
            raw_markdown=raw_md,
            low_confidence_sections=low_conf,
            flags=flags,
            model=settings.SOAP_MODEL,
            prompt_version=PROMPT_VERSION,
            agent_name=self.name,
        )

        ctx.audit.append(
            encounter_id=ctx.encounter_id,
            event_type="soap.generated",
            agent_name=self.name,
            actor=ctx.actor,
            summary=f"SOAP draft v{soap_note.version} generated ({len(raw_md)} chars)",
            payload={
                "soap_note_id": soap_note.id,
                "version": soap_note.version,
                "low_confidence_sections": low_conf,
                "flags": flags,
                "model": settings.SOAP_MODEL,
                "prompt_version": PROMPT_VERSION,
            },
        )

        return AgentResult(
            success=True,
            output={
                "soap_note_id": soap_note.id,
                "subjective":   subjective,
                "objective":    objective,
                "assessment":   assessment,
                "plan":         plan,
            },
            summary={
                "soap_note_id":  soap_note.id,
                "version":       soap_note.version,
                "model":         settings.SOAP_MODEL,
                "low_confidence_sections": low_conf,
                "flags": flags,
                "subjective_chars": len(subjective),
                "objective_chars":  len(objective),
                "assessment_chars": len(assessment),
                "plan_chars":       len(plan),
            },
        )

    @staticmethod
    def _render_markdown(s: str, o: str, a: str, p: str) -> str:
        return (
            f"### Subjective\n{s}\n\n"
            f"### Objective\n{o}\n\n"
            f"### Assessment\n{a}\n\n"
            f"### Plan\n{p}\n"
        )
