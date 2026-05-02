"""DEPRECATED — superseded by app.clients.openai_client and app.agents.transcription.

Retained as a thin shim so any external import keeps working.
"""
from app.clients.openai_client import openai_client


async def transcribe_audio(audio) -> tuple[str, str]:
    """Backward-compat helper kept so legacy code paths don't break."""
    contents = await audio.read()
    result = await openai_client.transcribe(
        filename=getattr(audio, "filename", "recording.webm"),
        content=contents,
        content_type=getattr(audio, "content_type", "audio/webm"),
    )
    duration = result.duration_seconds or 0.0
    m, s = divmod(int(round(duration)), 60)
    return result.text, (f"{m}m {s:02d}s" if m else f"{s}s")
