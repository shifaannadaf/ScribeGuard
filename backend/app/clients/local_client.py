"""
Local AI provider — free, on-device alternative to OpenAI.

Transcription:  faster-whisper  (CTranslate2-optimized port of OpenAI Whisper)
Chat:           Ollama HTTP API at OLLAMA_BASE_URL, default model llama3.2

Both pieces run locally so this provider has zero per-call cost. The first
transcription call downloads the Whisper weights into the HuggingFace cache;
subsequent calls reuse them.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any, Optional

import httpx

from app.clients.base import CompletionResult, TranscriptionResult
from app.config import settings


logger = logging.getLogger("scribeguard.local")


class LocalAIClient:
    """faster-whisper + Ollama implementation of the AIClient protocol."""

    provider = "local"

    def __init__(self):
        self._whisper_model = None  # lazy
        self._whisper_lock = asyncio.Lock()
        self._http: Optional[httpx.AsyncClient] = None

    # ── faster-whisper (transcription) ─────────────────────────────────

    async def _load_whisper(self):
        """Lazily load the faster-whisper model on first use."""
        if self._whisper_model is not None:
            return self._whisper_model
        async with self._whisper_lock:
            if self._whisper_model is not None:
                return self._whisper_model
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError(
                    "faster-whisper is not installed. Run "
                    "`pip install faster-whisper` to use SERVICE_PROVIDER=local."
                ) from exc

            model_size = settings.LOCAL_WHISPER_MODEL
            device = settings.LOCAL_WHISPER_DEVICE
            compute_type = settings.LOCAL_WHISPER_COMPUTE_TYPE
            logger.info(
                "Loading faster-whisper model=%s device=%s compute_type=%s",
                model_size, device, compute_type,
            )
            # Loading the model is heavy; do it off the event loop.
            self._whisper_model = await asyncio.to_thread(
                WhisperModel, model_size, device=device, compute_type=compute_type,
            )
            return self._whisper_model

    async def transcribe(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        model: Optional[str] = None,
    ) -> TranscriptionResult:
        # Agents pass OpenAI model names (e.g. "whisper-1") — they're meaningless
        # to faster-whisper. Always use the locally-configured model.
        model_name = settings.LOCAL_WHISPER_MODEL
        logger.info("faster-whisper transcription requested model=%s bytes=%d", model_name, len(content))

        whisper = await self._load_whisper()

        # faster-whisper accepts a file path, BytesIO, or numpy array. We write
        # the bytes to a temp file so codec sniffing (webm/ogg/wav) just works.
        suffix = Path(filename).suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            segments_iter, info = await asyncio.to_thread(
                whisper.transcribe,
                tmp_path,
                beam_size=1,
                vad_filter=True,
            )
            # `segments_iter` is a generator — exhaust it off-loop.
            segments = await asyncio.to_thread(list, segments_iter)
        finally:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass

        text = " ".join(seg.text.strip() for seg in segments).strip()
        duration = float(getattr(info, "duration", 0.0)) or None
        return TranscriptionResult(
            text=text,
            duration_seconds=duration,
            model=f"faster-whisper:{model_name}",
        )

    # ── Ollama (chat) ──────────────────────────────────────────────────

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=settings.OLLAMA_BASE_URL,
                timeout=settings.OLLAMA_TIMEOUT_SECONDS,
            )
        return self._http

    async def _ollama_chat(
        self,
        *,
        system: str,
        user: str,
        model: str,
        temperature: float,
        json_mode: bool,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"

        try:
            resp = await self.http.post("/api/chat", json=payload)
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"Ollama request failed at {settings.OLLAMA_BASE_URL}: {exc}. "
                "Is the Ollama server running? Try `ollama serve`."
            ) from exc

        if resp.status_code == 404:
            raise RuntimeError(
                f"Ollama model '{model}' not found. Pull it first: `ollama pull {model}`"
            )
        resp.raise_for_status()

        data = resp.json()
        message = data.get("message") or {}
        content = message.get("content") or ""
        return content

    async def chat_text(
        self,
        *,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
    ) -> CompletionResult:
        # Agents pass OpenAI model names (e.g. "gpt-4o-mini"); Ollama doesn't
        # have those. Always route through the locally-configured Ollama model.
        model_name = settings.OLLAMA_LLM_MODEL
        content = await self._ollama_chat(
            system=system, user=user, model=model_name,
            temperature=temperature, json_mode=False,
        )
        return CompletionResult(content=content, model=f"ollama:{model_name}")

    async def chat_json(
        self,
        *,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        model_name = settings.OLLAMA_LLM_MODEL
        # Ollama's `format: "json"` constrains output to valid JSON, but we
        # still defend against the model returning code fences or prose.
        raw = await self._ollama_chat(
            system=system, user=user, model=model_name,
            temperature=temperature, json_mode=True,
        )
        return _parse_json_loose(raw)


def _parse_json_loose(raw: str) -> dict[str, Any]:
    """Robustly parse a model JSON response that may include code fences or prose."""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Strip markdown fences
    cleaned = raw.strip().strip("`")
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Last resort: extract the first {...} block
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Local model returned non-JSON output: {raw[:200]}") from exc
    raise RuntimeError(f"Local model returned non-JSON output: {raw[:200]}")
