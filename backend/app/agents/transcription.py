"""
Agent 2 — Transcription Agent.

Reads the audio bytes the IntakeAgent stored to disk, calls OpenAI Whisper,
cleans + normalizes the result, performs lightweight quality checks, and
persists a Transcript artifact downstream agents can consume.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from app.agents import Agent, AgentContext, AgentResult
from app.agents.audio_storage import AudioStorage
from app.agents.exceptions import AgentExecutionError, AgentValidationError
from app.clients import ai_client
from app.config import settings
from app.models import ProcessingStage


logger = logging.getLogger("scribeguard.agents.transcription")


class TranscriptionAgent(Agent[dict[str, Any]]):
    name = "TranscriptionAgent"
    version = "1.1.0"
    description = (
        "Transcribes the encounter audio using Whisper, cleans the output, "
        "and emits a Transcript artifact with quality signals."
    )

    def __init__(self):
        self.storage = AudioStorage(settings.AUDIO_STORAGE_DIR)

    def input_summary(self, ctx: AgentContext) -> dict[str, Any]:
        return {
            "encounter_id": ctx.encounter_id,
            "audio_path":   ctx.encounter.audio_path,
            "audio_size":   ctx.encounter.audio_size_bytes,
            "model":        settings.WHISPER_MODEL,
        }

    async def run(self, ctx: AgentContext) -> AgentResult[dict[str, Any]]:
        enc = ctx.encounter
        if not enc.audio_path:
            raise AgentValidationError("Cannot transcribe — encounter has no audio file.")

        audio_bytes = self.storage.read(enc.audio_path)
        if not audio_bytes:
            raise AgentValidationError(
                f"Audio file missing on disk for encounter {enc.id} at {enc.audio_path}."
            )

        ctx.encounters.set_processing_stage(enc, ProcessingStage.transcribing)

        # ── Whisper call ────────────────────────────────────────────────
        try:
            tx = await ai_client.transcribe(
                filename=enc.audio_filename or "recording.webm",
                content=audio_bytes,
                content_type=enc.audio_mime or "audio/webm",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Whisper call failed for encounter %s", enc.id)
            raise AgentExecutionError(f"Whisper transcription failed: {exc}") from exc

        raw = (tx.text or "").strip()
        if not raw:
            raise AgentExecutionError("Whisper returned an empty transcript.")

        cleaned = self._clean(raw)
        score, issues = self._score_quality(cleaned, tx.duration_seconds)

        if tx.duration_seconds:
            ctx.encounters.update_audio_duration(enc, tx.duration_seconds)

        transcript = ctx.transcripts.create(
            encounter_id=enc.id,
            raw_text=raw,
            formatted_text=cleaned,
            duration_seconds=tx.duration_seconds,
            model=tx.model,
            quality_score=score,
            quality_issues=issues,
        )

        ctx.audit.append(
            encounter_id=enc.id,
            event_type="transcript.created",
            agent_name=self.name,
            actor=ctx.actor,
            summary=f"Transcribed {len(raw)} chars in {tx.duration_seconds or 0:.1f}s audio",
            payload={
                "transcript_id":     transcript.id,
                "model":              tx.model,
                "duration_seconds":   tx.duration_seconds,
                "word_count":         len(raw.split()),
                "quality_score":      score,
                "quality_issues":     issues,
            },
        )

        return AgentResult(
            success=True,
            output={"transcript_id": transcript.id, "text": cleaned, "raw": raw},
            summary={
                "transcript_id":   transcript.id,
                "word_count":      len(raw.split()),
                "duration_seconds": tx.duration_seconds,
                "quality_score":   score,
                "quality_issues":  issues,
                "model":           tx.model,
            },
        )

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _clean(text: str) -> str:
        """Light normalization — collapse whitespace, fix capitalization at sentence starts."""
        # Collapse repeated whitespace
        cleaned = re.sub(r"\s+", " ", text).strip()
        # Capitalize after sentence-terminating punctuation followed by a space
        cleaned = re.sub(
            r"([.!?]\s+)([a-z])",
            lambda m: m.group(1) + m.group(2).upper(),
            cleaned,
        )
        return cleaned

    @staticmethod
    def _score_quality(text: str, duration: Optional[float]) -> tuple[float, list[str]]:
        """Tiny heuristic. We're not pretending this is real WER — just enough to
        flag obviously bad audio so the UI can surface it to the physician."""
        issues: list[str] = []
        word_count = len(text.split())

        # 1) Too short for a clinical encounter
        if duration and duration < 10:
            issues.append("recording_under_10_seconds")

        # 2) Suspiciously low words/second (transcription likely incomplete)
        if duration and duration > 0:
            wps = word_count / duration
            if wps < 0.5:
                issues.append("low_words_per_second")

        # 3) Heavy filler content
        fillers = ("um", "uh", "you know", "like")
        filler_hits = sum(text.lower().count(f) for f in fillers)
        if word_count and filler_hits / max(word_count, 1) > 0.05:
            issues.append("heavy_filler_words")

        # 4) Missing speaker cues — purely informational
        if "doctor" not in text.lower() and "patient" not in text.lower():
            issues.append("no_explicit_speaker_cues")

        score = 1.0 - 0.15 * len(issues)
        return max(0.1, round(score, 2)), issues
