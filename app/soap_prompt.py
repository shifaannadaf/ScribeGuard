"""
soap_prompt.py
==============
Production module for SOAP note generation via GPT-4.

This is the output of Sprint 1 prompt engineering work.
The system prompt (V2) lives here as a constant so the FastAPI
/generate-note endpoint can import it directly.

Prompt version: v2
Model: gpt-4o
Temperature: 0.2
"""

import json
from typing import Any

# ── System Prompt (V2 — production-ready) ─────────────────────────────────────

SOAP_SYSTEM_PROMPT = """You are a clinical documentation assistant. Your task is to read a raw conversation transcript between a physician and a patient (and possibly other speakers such as nurses, medical assistants, or family members) and produce a structured SOAP note as a single valid JSON object.

---

SOAP Section Definitions:

chief_complaint: One to two sentences stating the primary reason for the visit, in clinical language. Extract this from the opening of the encounter.

historian: Who provided the history. Use exactly one of: "patient", "parent/guardian", "spouse", "caregiver", "other". Default to "patient" if only the patient is speaking.

subjective (S): Everything the patient (or historian) reports — symptoms, their onset, duration, severity, quality, location, radiation, aggravating/relieving factors, associated symptoms, relevant past medical history, current medications mentioned by the patient, allergies, and social/family history as stated.

objective (O): Measurable, directly observed, or test-based data — vital signs, physical examination findings, laboratory values, imaging results, ECG findings, screening scores (PHQ-9, GAD-7, etc.). Do not include anything the patient merely reports in this section.

assessment (A): The physician's clinical impression — diagnoses and/or differential diagnoses, numbered if multiple. Include supporting evidence from the objective data where stated.

plan (P): All actions decided upon — prescriptions, investigations ordered, referrals, patient education, lifestyle modifications, safety planning, and follow-up instructions. Do not include follow-up timing here; that goes in the follow_up field.

medications_new: An array of medications prescribed, adjusted, or discontinued at THIS visit. Each entry is an object with:
  - name: generic or brand name as stated
  - dose: strength and unit (e.g., "500 mg", "10 mg/5 mL")
  - route: "oral", "IV", "sublingual", "topical", "inhaled", "subcutaneous", etc.
  - frequency: e.g., "twice daily", "once daily at bedtime", "every 6-8 hours as needed"
  - duration: course length if stated (e.g., "10 days"), or null if ongoing/not specified
  - status: one of "new" (first-time prescription), "increased" (dose increased), "decreased" (dose decreased), "discontinued" (explicitly stopped this visit)
  - indication: brief reason for the medication if stated or clearly inferable

medications_existing: An array of medications the patient is currently taking that were mentioned but NOT changed this visit. Each entry has: name, dose, route, frequency (use "" for unknown fields).

follow_up: An object with:
  - timeframe: when the patient should return (e.g., "3 months"), or "" if not stated
  - conditions: array of strings — return-sooner or ER conditions. Empty array if none stated.

---

Output Rules:

1. Your entire response MUST be a single raw JSON object. Do not include any text before or after the JSON. Do not use markdown code fences. Do not apologize, explain, or add commentary. If a field has no information, use an empty string "" or empty array [] — never omit a required key.

2. Do not hallucinate. Only include information explicitly stated or unambiguously implied in the transcript.

3. Strip filler words. Ignore "uh", "um", "like", "you know", false starts, and repeated words. Use context to complete interrupted sentences.

4. Handle crosstalk. When two speakers overlap, use surrounding context to determine the most clinically relevant meaning. Prioritize the physician's clinical statements.

5. Multi-party encounters. Only attribute clinical assessment and plan content to the physician. Nursing or MA statements may contribute to the objective section. Family members or caregivers contribute to the subjective section only.

6. Convert casual language to clinical language. "My tummy hurts" -> "abdominal pain". Maintain accuracy; do not over-interpret.

7. Medications precision. Distinguish carefully between medications newly prescribed today (medications_new) versus those the patient was already taking before this visit (medications_existing). If the physician explicitly increases, decreases, or discontinues a previously existing medication, it goes in medications_new with the appropriate status field.

8. Pediatric/proxy encounters. When a parent, guardian, or caregiver is the primary historian, set historian accordingly and include the patient's weight in the objective section if stated.

---

Required JSON Schema:
{
  "chief_complaint": "",
  "historian": "patient",
  "subjective": "",
  "objective": "",
  "assessment": "",
  "plan": "",
  "medications_new": [
    {
      "name": "",
      "dose": "",
      "route": "",
      "frequency": "",
      "duration": null,
      "status": "new",
      "indication": ""
    }
  ],
  "medications_existing": [
    {
      "name": "",
      "dose": "",
      "route": "",
      "frequency": ""
    }
  ],
  "follow_up": {
    "timeframe": "",
    "conditions": []
  }
}"""

# ── Model config ───────────────────────────────────────────────────────────────

SOAP_MODEL = "gpt-4o"
SOAP_TEMPERATURE = 0.2
SOAP_MAX_TOKENS = 1800

# ── Generation function ────────────────────────────────────────────────────────

def generate_soap_note(client: Any, transcript: str) -> dict:
    """
    Generate a structured SOAP note from a raw transcript.

    Args:
        client: An openai.OpenAI client instance
        transcript: Raw transcript text from Whisper or manual input

    Returns:
        dict with keys:
            - soap: the parsed SOAP note dict (all V2 schema fields)
            - raw: the raw string response from GPT-4

    Raises:
        ValueError: If GPT-4 returns malformed JSON despite instructions
    """
    response = client.chat.completions.create(
        model=SOAP_MODEL,
        messages=[
            {"role": "system", "content": SOAP_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Please convert the following clinical transcript into a SOAP note:\n\n"
                    + transcript
                ),
            },
        ],
        temperature=SOAP_TEMPERATURE,
        max_tokens=SOAP_MAX_TOKENS,
    )

    raw = response.choices[0].message.content.strip()

    # Defensive strip of markdown fences in case the model wraps output
    if raw.startswith("```"):
        parts = raw.split("```")
        # parts[1] is the fenced content (possibly prefixed with "json\n")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        soap = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"GPT-4 returned non-JSON output. Raw response:\n{raw}"
        ) from exc

    return {"soap": soap, "raw": raw}


# ── Schema validation helper ───────────────────────────────────────────────────

REQUIRED_TOP_LEVEL_KEYS = {
    "chief_complaint",
    "historian",
    "subjective",
    "objective",
    "assessment",
    "plan",
    "medications_new",
    "medications_existing",
    "follow_up",
}

REQUIRED_MED_NEW_KEYS = {"name", "dose", "route", "frequency", "duration", "status", "indication"}
REQUIRED_MED_EXISTING_KEYS = {"name", "dose", "route", "frequency"}
VALID_STATUSES = {"new", "increased", "decreased", "discontinued"}
VALID_HISTORIANS = {"patient", "parent/guardian", "spouse", "caregiver", "other"}


def validate_soap_note(soap: dict) -> list[str]:
    """
    Validate a parsed SOAP note against the V2 schema.

    Returns a list of validation error strings. Empty list means valid.
    """
    errors = []

    missing = REQUIRED_TOP_LEVEL_KEYS - set(soap.keys())
    if missing:
        errors.append(f"Missing top-level keys: {missing}")
        return errors  # Can't validate further without required keys

    if soap.get("historian") not in VALID_HISTORIANS:
        errors.append(
            f"Invalid historian value: '{soap.get('historian')}'. "
            f"Must be one of: {VALID_HISTORIANS}"
        )

    for key in ("chief_complaint", "subjective", "objective", "assessment", "plan"):
        if not isinstance(soap.get(key), str):
            errors.append(f"Field '{key}' must be a string")

    if not isinstance(soap.get("medications_new"), list):
        errors.append("'medications_new' must be an array")
    else:
        for i, med in enumerate(soap["medications_new"]):
            missing_med = REQUIRED_MED_NEW_KEYS - set(med.keys())
            if missing_med:
                errors.append(f"medications_new[{i}] missing keys: {missing_med}")
            if med.get("status") not in VALID_STATUSES:
                errors.append(
                    f"medications_new[{i}].status '{med.get('status')}' invalid. "
                    f"Must be one of: {VALID_STATUSES}"
                )

    if not isinstance(soap.get("medications_existing"), list):
        errors.append("'medications_existing' must be an array")
    else:
        for i, med in enumerate(soap["medications_existing"]):
            missing_med = REQUIRED_MED_EXISTING_KEYS - set(med.keys())
            if missing_med:
                errors.append(f"medications_existing[{i}] missing keys: {missing_med}")

    follow_up = soap.get("follow_up", {})
    if not isinstance(follow_up, dict):
        errors.append("'follow_up' must be an object")
    else:
        if "timeframe" not in follow_up:
            errors.append("'follow_up.timeframe' is required")
        if "conditions" not in follow_up or not isinstance(follow_up.get("conditions"), list):
            errors.append("'follow_up.conditions' must be an array")

    return errors
