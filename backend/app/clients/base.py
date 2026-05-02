"""
AI provider abstraction.

Both the OpenAI client and the local (faster-whisper + Ollama) client
implement the same interface so the agents stay provider-agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    duration_seconds: Optional[float]
    model: str


@dataclass(frozen=True)
class CompletionResult:
    content: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


@runtime_checkable
class AIClient(Protocol):
    """Interface every AI provider implementation must satisfy."""

    provider: str

    async def transcribe(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        model: Optional[str] = None,
    ) -> TranscriptionResult: ...

    async def chat_text(
        self,
        *,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
    ) -> CompletionResult: ...

    async def chat_json(
        self,
        *,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]: ...
