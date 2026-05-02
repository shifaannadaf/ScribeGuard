"""
Test the structured LLM extraction against 10 CSV dialogues.
Run from the project root:
    python test_extraction.py
"""

import csv
import json
import asyncio
import os
from openai import AsyncOpenAI

API_KEY = os.getenv("OPENAI_API_KEY") or open("backend/.env").read().split("OPENAI_API_KEY=")[1].split("\n")[0].strip()
CSV_PATH = "train.csv"
SAMPLE_EVERY = 925  # pick 1 row every ~925 to get 10 diverse samples from 9250 rows

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
  "immunizations": [
    {"vaccine": "string", "date": "string"}
  ],
  "plan": "string — recommended next steps, follow-ups, referrals"
}

Rules:
- Use null for unknown vitals, empty arrays [] if nothing is mentioned.
- Infer ICD-10 codes where clearly applicable; leave empty string if unsure.
- Do NOT invent data — only extract what is explicitly or strongly implied in the transcript."""

client = AsyncOpenAI(api_key=API_KEY)


async def extract(dialogue: str, index: int) -> dict:
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": EXTRACT_SYSTEM},
            {"role": "user",   "content": f"Transcript:\n{dialogue}"},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


async def main():
    # Sample 10 rows evenly spaced through the CSV
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i % SAMPLE_EVERY == 0:
                rows.append((i, row["dialogue"]))
            if len(rows) == 10:
                break

    print(f"Running extraction on {len(rows)} dialogues...\n{'='*60}\n")

    tasks = [extract(dialogue, i) for i, dialogue in rows]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    passed = failed = 0
    for (row_idx, dialogue), result in zip(rows, results):
        print(f"Row {row_idx:>6} | ", end="")
        if isinstance(result, Exception):
            print(f"FAILED — {result}")
            failed += 1
            continue

        cc      = result.get("chief_complaint", "")[:80]
        diags   = result.get("diagnoses", [])
        meds    = result.get("active_medications", [])
        allergies = result.get("allergies", [])
        vitals  = {k: v for k, v in (result.get("vitals") or {}).items() if v is not None}

        print(f"CC: {cc}")
        print(f"         | Diagnoses: {len(diags)}  Meds: {len(meds)}  Allergies: {len(allergies)}  Vitals: {list(vitals.keys())}")
        if diags:
            print(f"         | Dx: {diags[0]['description']} [{diags[0]['icd10_code']}]")
        if meds:
            print(f"         | Rx: {meds[0]['name']} {meds[0].get('dose','')} {meds[0].get('frequency','')}")
        print()
        passed += 1

    print(f"{'='*60}")
    print(f"Passed: {passed}/10   Failed: {failed}/10")

    # Save full results to JSON for inspection
    out = [{"row": row_idx, "dialogue_snippet": d[:200], "extraction": r}
           for (row_idx, d), r in zip(rows, results) if not isinstance(r, Exception)]
    with open("extraction_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print("Full results saved to extraction_results.json")


asyncio.run(main())
