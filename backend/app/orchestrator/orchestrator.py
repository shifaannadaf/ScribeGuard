"""
ScribeGuard agent orchestrator.

Responsibilities:
    1. Run a single agent with retries, persistence, and audit emission.
    2. Drive the full end-to-end pipeline by calling each agent in sequence
       and committing the encounter's state transitions atomically per stage.

Design notes:
    - The orchestrator is the single place that mutates `encounter.processing_stage`
      across stage boundaries. Individual agents may set transient stages
      (e.g. "transcribing") but stage transitions are always orchestrator-driven.
    - We commit the SQLAlchemy session at the end of every stage. That means
      a partial pipeline run is fully durable: a later call to `run_pipeline`
      can resume from where it failed.
    - Audit + agent-run rows are written even on failure, so the audit trail
      never has gaps.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.agents import Agent, AgentContext, AgentResult
from app.agents.exceptions import AgentError, AgentExecutionError, AgentValidationError
from app.config import settings
from app.models import (
    AgentRunStatus,
    Encounter,
    EncounterStatus,
    ProcessingStage,
)
from app.orchestrator.registry import AgentRegistry


logger = logging.getLogger("scribeguard.orchestrator")


# ── Per-stage configuration ────────────────────────────────────────────────

@dataclass(frozen=True)
class PipelineStep:
    agent_name: str
    pre_stage: ProcessingStage   # stage to set before running
    post_stage: ProcessingStage  # stage to set on success
    optional: bool = False       # if True, failure does not break the pipeline


# Note: PhysicianReview is *not* in the auto-pipeline — it's a manual gate.
DEFAULT_PIPELINE: tuple[PipelineStep, ...] = (
    PipelineStep(
        agent_name="EncounterIntakeAgent",
        pre_stage=ProcessingStage.audio_received,
        post_stage=ProcessingStage.audio_received,
    ),
    PipelineStep(
        agent_name="TranscriptionAgent",
        pre_stage=ProcessingStage.transcribing,
        post_stage=ProcessingStage.transcribed,
    ),
    PipelineStep(
        agent_name="ClinicalNoteGenerationAgent",
        pre_stage=ProcessingStage.generating_soap,
        post_stage=ProcessingStage.soap_drafted,
    ),
    PipelineStep(
        agent_name="MedicationExtractionAgent",
        pre_stage=ProcessingStage.extracting_meds,
        post_stage=ProcessingStage.ready_for_review,
    ),
)


@dataclass
class OrchestratorOutcome:
    encounter_id: str
    final_stage: ProcessingStage
    status: EncounterStatus
    transcript_id: Optional[int] = None
    soap_note_id: Optional[int] = None
    medications_extracted: int = 0
    duration_ms: float = 0.0
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


# ───────────────────────────────────────────────────────────────────────────


class AgentOrchestrator:
    """Coordinates agent execution against an Encounter."""

    def __init__(
        self,
        db: Session,
        registry: AgentRegistry,
        *,
        max_retries: Optional[int] = None,
        retry_base_delay: Optional[float] = None,
    ):
        self.db = db
        self.registry = registry
        self.max_retries = max_retries if max_retries is not None else settings.AGENT_MAX_RETRIES
        self.retry_base_delay = retry_base_delay if retry_base_delay is not None else settings.AGENT_RETRY_BASE_DELAY_SECONDS

    # ── Single-agent execution ─────────────────────────────────────────

    async def run_agent(
        self,
        agent_name: str,
        encounter: Encounter,
        *,
        actor: str = "system",
        payload: Optional[dict[str, Any]] = None,
    ) -> AgentResult:
        """Run one agent with retries, persistence, and audit emission."""
        agent = self.registry.require(agent_name)
        ctx = AgentContext(
            db=self.db,
            encounter=encounter,
            actor=actor,
            payload=payload or {},
        )

        last_error: Optional[BaseException] = None
        attempts = max(1, 1 + self.max_retries)
        for attempt in range(1, attempts + 1):
            run = ctx.agent_runs.create_running(
                encounter_id=encounter.id,
                agent_name=agent.name,
                agent_version=agent.version,
                attempt=attempt,
                input_summary=agent.input_summary(ctx),
            )
            t0 = time.perf_counter()
            try:
                logger.info("Agent %s running (attempt %d) for encounter %s", agent.name, attempt, encounter.id)
                result = await agent.run(ctx)
                duration_ms = (time.perf_counter() - t0) * 1000.0

                ctx.agent_runs.finish(
                    run,
                    status=AgentRunStatus.succeeded if result.success else AgentRunStatus.failed,
                    output_summary=result.summary,
                    duration_ms=duration_ms,
                )

                if result.success:
                    self._emit_audit(
                        ctx,
                        event_type=f"{agent.name}.completed",
                        agent_name=agent.name,
                        actor=actor,
                        summary=f"{agent.name} succeeded in {duration_ms:.0f}ms",
                        payload={"attempt": attempt, **result.summary},
                    )
                    self.db.commit()
                    return result

                # Agent reported a soft failure — treat as non-retriable
                err_msg = result.summary.get("error") or "Agent reported failure"
                self._emit_audit(
                    ctx,
                    event_type=f"{agent.name}.failed",
                    agent_name=agent.name,
                    actor=actor,
                    severity="error",
                    summary=err_msg,
                    payload={"attempt": attempt, **result.summary},
                )
                self.db.commit()
                return result

            except AgentValidationError as exc:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                ctx.agent_runs.finish(
                    run,
                    status=AgentRunStatus.failed,
                    error_message=str(exc),
                    error_type=exc.__class__.__name__,
                    duration_ms=duration_ms,
                )
                self._emit_audit(
                    ctx,
                    event_type=f"{agent.name}.invalid_input",
                    agent_name=agent.name,
                    actor=actor,
                    severity="error",
                    summary=str(exc),
                    payload={"attempt": attempt},
                )
                self.db.commit()
                raise

            except (AgentExecutionError, Exception) as exc:  # noqa: BLE001
                duration_ms = (time.perf_counter() - t0) * 1000.0
                last_error = exc
                ctx.agent_runs.finish(
                    run,
                    status=AgentRunStatus.failed,
                    error_message=str(exc),
                    error_type=exc.__class__.__name__,
                    duration_ms=duration_ms,
                )
                retriable = isinstance(exc, AgentExecutionError) or not isinstance(exc, AgentError)
                self._emit_audit(
                    ctx,
                    event_type=f"{agent.name}.exception",
                    agent_name=agent.name,
                    actor=actor,
                    severity="error",
                    summary=f"{exc.__class__.__name__}: {exc}",
                    payload={"attempt": attempt, "retriable": retriable},
                )
                self.db.commit()
                if retriable and attempt < attempts:
                    delay = self.retry_base_delay * attempt
                    logger.warning(
                        "Agent %s attempt %d/%d failed: %s — retrying in %.1fs",
                        agent.name, attempt, attempts, exc, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        if last_error:
            raise last_error
        raise RuntimeError("Unreachable: orchestrator retry loop exited unexpectedly")

    # ── End-to-end pipeline ────────────────────────────────────────────

    async def run_pipeline(
        self,
        encounter: Encounter,
        *,
        actor: str = "system",
    ) -> OrchestratorOutcome:
        """Run intake → transcription → SOAP → medication extraction in order.

        Stops short of physician review (which is a manual gate) and
        OpenMRS submission (which only happens after explicit approval).
        """
        outcome = OrchestratorOutcome(
            encounter_id=encounter.id,
            final_stage=encounter.processing_stage,
            status=encounter.status,
        )
        t0 = time.perf_counter()
        repo = None
        for step in DEFAULT_PIPELINE:
            try:
                # Move into the pre-stage so the UI can show "transcribing", etc.
                ctx_repo_session = AgentContext(db=self.db, encounter=encounter)
                ctx_repo_session.encounters.set_processing_stage(encounter, step.pre_stage)
                self.db.commit()

                result = await self.run_agent(step.agent_name, encounter, actor=actor)

                # Capture meaningful IDs for the response
                if step.agent_name == "TranscriptionAgent":
                    outcome.transcript_id = result.summary.get("transcript_id")
                elif step.agent_name == "ClinicalNoteGenerationAgent":
                    outcome.soap_note_id = result.summary.get("soap_note_id")
                elif step.agent_name == "MedicationExtractionAgent":
                    outcome.medications_extracted = int(result.summary.get("count", 0))

                # Advance to the post-stage on success
                if result.success:
                    AgentContext(db=self.db, encounter=encounter).encounters.set_processing_stage(
                        encounter, step.post_stage
                    )
                    self.db.commit()
                    outcome.final_stage = step.post_stage
                else:
                    msg = result.summary.get("error", f"{step.agent_name} failed")
                    outcome.errors.append(msg)
                    if not step.optional:
                        AgentContext(db=self.db, encounter=encounter).encounters.set_error(encounter, msg)
                        self.db.commit()
                        outcome.final_stage = ProcessingStage.failed
                        outcome.status = EncounterStatus.failed
                        break
            except Exception as exc:  # noqa: BLE001
                outcome.errors.append(f"{step.agent_name}: {exc}")
                if not step.optional:
                    AgentContext(db=self.db, encounter=encounter).encounters.set_error(encounter, str(exc))
                    self.db.commit()
                    outcome.final_stage = ProcessingStage.failed
                    outcome.status = EncounterStatus.failed
                    break

        outcome.duration_ms = (time.perf_counter() - t0) * 1000.0
        return outcome

    # ── Internals ──────────────────────────────────────────────────────

    def _emit_audit(self, ctx: AgentContext, **kwargs):
        if not settings.AGENT_AUDIT_ENABLED:
            return
        ctx.audit.append(encounter_id=ctx.encounter.id, **kwargs)
