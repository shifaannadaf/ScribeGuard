import time
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def transcribe_audio(audio) -> tuple[str, str]:
    """Returns (transcript_text, duration_string)."""
    t0 = time.monotonic()
    contents = await audio.read()
    result = await client.audio.transcriptions.create(
        model="whisper-1",
        file=(audio.filename, contents, audio.content_type),
    )
    elapsed = time.monotonic() - t0
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    duration = f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"
    return result.text, duration
