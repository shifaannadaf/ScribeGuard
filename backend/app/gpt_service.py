import json
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

EXTRACT_SYSTEM = """You are a clinical documentation AI. Extract structured clinical data from a doctor-patient transcript.

Return ONLY valid JSON with this exact shape — no markdown, no extra text:
{
  "chief_complaint": "string — main reason for the visit in the patient's own words",
  "clinical_summary": "string — 2-3 sentence clinical summary written by the doctor",
  "vitals": {
    "height_cm":               number or null,
    "weight_kg":               number or null,
    "temperature_c":           number or null,
    "blood_pressure_systolic": number or null,
    "blood_pressure_diastolic":number or null,
    "spo2_pct":                number or null,
    "resp_rate":               number or null,
    "pulse":                   number or null
  },
  "diagnoses": [
    {"icd10_code": "string", "description": "string", "status": "Presumed|Confirmed|Ruled Out"}
  ],
  "active_medications": [
    {"name": "string", "dose": "string", "route": "string", "frequency": "string"}
  ],
  "past_medications": [
    {"name": "string", "reason_stopped": "string"}
  ],
  "allergies": [
    {"allergen": "string", "reaction": "string", "severity": "Mild|Moderate|Severe"}
  ],
"plan": "string — recommended next steps, follow-ups, referrals"
}

Rules:
- Use null for unknown vitals, empty arrays [] if nothing is mentioned.
- Infer ICD-10 codes where clearly applicable; leave empty string if unsure.
- Do NOT invent data — only extract what is explicitly or strongly implied in the transcript."""

CHAT_SYSTEM = """You are ScribeGuard, an AI clinical documentation assistant with access to complete patient history.

---CURRENT ENCOUNTER TRANSCRIPT---
{transcript}
---END TRANSCRIPT---

---PATIENT HISTORY FROM EHR---
{patient_history}
---END PATIENT HISTORY---

You can answer questions about:
1. The current encounter (from the transcript)
2. The patient's medical history (from the EHR)
3. Connections between current symptoms and past conditions
4. Potential drug interactions with existing medications
5. Recommendations based on their full clinical picture

Answer questions concisely and accurately. Format medications, diagnoses, and care plan items as markdown bold where helpful.
If something is not available in either source, say so clearly.
When making clinical suggestions, always consider the patient's complete medical history."""


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
    """Returns structured clinical data extracted from the transcript."""
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": EXTRACT_SYSTEM},
            {"role": "user",   "content": f"Transcript:\n{transcript}"},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


async def chat_with_transcript(
    transcript: str, 
    message: str, 
    history: list[dict],
    patient_history: str = "No patient history available."
) -> str:
    """Returns assistant reply string with patient history context."""
    system = CHAT_SYSTEM.format(transcript=transcript, patient_history=patient_history)
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
