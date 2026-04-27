import json
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SOAP_SYSTEM = """You are a clinical documentation AI. Extract structured data from a doctor-patient transcript.

Return ONLY valid JSON with this exact shape:
{
  "medications": [{"name": str, "dose": str, "route": str, "frequency": str, "start_date": str}],
  "allergies":   [{"allergen": str, "reaction": str, "severity": "Mild|Moderate|Severe"}],
  "diagnoses":   [{"icd10_code": str, "description": str, "status": "Presumed|Confirmed|Ruled Out"}]
}

Rules:
- Use empty arrays [] if nothing is mentioned.
- Infer ICD-10 codes where possible; leave empty string if unsure.
- start_date: use ISO date if mentioned, else empty string.
- Do NOT include any text outside the JSON."""

CHAT_SYSTEM = """You are ScribeGuard, an AI clinical documentation assistant.
You have access to the following doctor-patient transcript:

---TRANSCRIPT---
{transcript}
---END TRANSCRIPT---

Answer questions concisely and accurately based only on this transcript.
Format medications, diagnoses, and care plan items as markdown bold where helpful.
If something is not in the transcript, say so clearly."""


DIARIZE_SYSTEM = """You are a medical transcription formatter.

Given a raw transcript of a doctor-patient consultation, reformat it with speaker labels.
Use "Doctor:" and "Patient:" as prefixes. Put each speaker turn on its own line separated by a blank line.

Rules:
- Use context clues to identify who is speaking (doctor asks clinical questions, patient describes symptoms).
- Do NOT add, remove, or change any words — only add the speaker labels.
- If you cannot tell who is speaking, use "Doctor:" as a default for clinical statements.
- Output ONLY the formatted transcript, no explanations."""


async def format_transcript(raw: str) -> str:
    """Takes raw Whisper text, returns speaker-labelled transcript."""
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": DIARIZE_SYSTEM},
            {"role": "user",   "content": raw},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content.strip()


async def generate_note(transcript: str) -> dict:
    """Returns dict with medications, allergies, diagnoses lists."""
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SOAP_SYSTEM},
            {"role": "user",   "content": f"Transcript:\n{transcript}"},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


async def chat_with_transcript(transcript: str, message: str, history: list[dict]) -> str:
    """Returns assistant reply string."""
    system = CHAT_SYSTEM.format(transcript=transcript)
    messages = [{"role": "system", "content": system}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
    )
    return resp.choices[0].message.content
