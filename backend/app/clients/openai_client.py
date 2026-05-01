"""
OpenAI client wrapper used by the Whisper- and GPT-backed agents.

Centralizing both the SDK instance and the prompt-execution helpers in one
place keeps the agents free of SDK boilerplate and gives us a single place
to add timeouts, retries, and instrumentation.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from openai import AsyncOpenAI

from app.clients.base import CompletionResult, TranscriptionResult
from app.config import settings


logger = logging.getLogger("scribeguard.openai")


class OpenAIClient:
    """Thin async wrapper around the OpenAI SDK."""

    provider = "openai"

    def __init__(self, api_key: Optional[str] = None, timeout: Optional[float] = None):
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._timeout = timeout or settings.OPENAI_TIMEOUT_SECONDS
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY is not configured. Set it in your .env file."
                )
            self._client = AsyncOpenAI(api_key=self._api_key, timeout=self._timeout)
        return self._client

    # ── Whisper ────────────────────────────────────────────────────────

    async def transcribe(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        model: Optional[str] = None,
    ) -> TranscriptionResult:
        model = model or settings.WHISPER_MODEL
        logger.info("Whisper transcription requested model=%s bytes=%d", model, len(content))
        resp = await self.client.audio.transcriptions.create(
            model=model,
            file=(filename, content, content_type),
            response_format="verbose_json",
        )
        # `verbose_json` returns an object with `.text` and `.duration`
        text = getattr(resp, "text", "") or ""
        duration = getattr(resp, "duration", None)
        return TranscriptionResult(text=text, duration_seconds=duration, model=model)

    # ── Chat / JSON completions ────────────────────────────────────────

    async def chat_text(
        self,
        *,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
    ) -> CompletionResult:
        model = model or settings.SOAP_MODEL
        resp = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=temperature,
        )
        choice = resp.choices[0]
        usage = getattr(resp, "usage", None)
        return CompletionResult(
            content=choice.message.content or "",
            model=model,
            prompt_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
            completion_tokens=getattr(usage, "completion_tokens", None) if usage else None,
        )

    async def chat_json(
        self,
        *,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        model = model or settings.SOAP_MODEL
        resp = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("Model returned invalid JSON, attempting recovery: %s", exc)
            # Be defensive: model occasionally wraps JSON in fences
            cleaned = raw.strip().strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            return json.loads(cleaned)


openai_client = OpenAIClient()
