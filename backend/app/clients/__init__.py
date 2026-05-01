"""External integration clients (OpenAI / local, OpenMRS, ...).

`ai_client` is the single entry point agents should use for transcription
and chat. The concrete implementation is selected at startup from the
SERVICE_PROVIDER setting:

    SERVICE_PROVIDER=openai   → OpenAI Whisper + OpenAI GPT  (default)
    SERVICE_PROVIDER=local    → faster-whisper + Ollama llama3.2 (free)
"""
from __future__ import annotations

import logging

from app.clients.base import AIClient, CompletionResult, TranscriptionResult
from app.config import settings


logger = logging.getLogger("scribeguard.clients")


def _build_ai_client() -> AIClient:
    provider = (settings.SERVICE_PROVIDER or "openai").strip().lower()

    if provider == "openai":
        from app.clients.openai_client import OpenAIClient
        logger.info("AI provider: openai (Whisper + %s)", settings.SOAP_MODEL)
        return OpenAIClient()

    if provider == "local":
        from app.clients.local_client import LocalAIClient
        logger.info(
            "AI provider: local (faster-whisper:%s + ollama:%s)",
            settings.LOCAL_WHISPER_MODEL,
            settings.OLLAMA_LLM_MODEL,
        )
        return LocalAIClient()

    raise RuntimeError(
        f"Unknown SERVICE_PROVIDER={provider!r}. "
        "Use 'openai' or 'local'."
    )


ai_client: AIClient = _build_ai_client()


__all__ = ["ai_client", "AIClient", "CompletionResult", "TranscriptionResult"]
