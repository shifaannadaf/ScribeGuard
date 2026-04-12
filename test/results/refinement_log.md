# Prompt Refinement Log

## Overview

This document tracks the findings from each test round and the reasoning behind each change made to the system prompt. The goal is a prompt that produces consistent, machine-parseable, clinically accurate SOAP notes across all encounter types.

---

## V1 → V2 Changes

### Change 1: Split `medications` into `medications_new` + `medications_existing`

**Problem found in:** Transcripts 02 (Chest Pain), 03 (Diabetes)

**What happened:**  
V1 produced a single `medications` array that mixed:
- Drugs prescribed this visit (e.g., aspirin 325 mg for acute ACS)
- Drugs the patient was already taking (e.g., lisinopril mentioned in history)
- Drugs with adjusted doses (e.g., sertraline increased from 100 to 150 mg)

This is dangerous for downstream write-back — the system cannot distinguish what to write to OpenMRS as a new order vs. what already exists in the medication list.

**Fix:**  
Replace `medications: []` with two arrays:
```json
"medications_new": [...],      // prescribed or dose-changed this visit
"medications_existing": [...]  // mentioned as current, not changed
```

Each entry in `medications_new` now includes a `status` field:
- `"new"` — first-time prescription
- `"increased"` — dose increased
- `"decreased"` — dose decreased  
- `"discontinued"` — explicitly stopped

---

### Change 2: Add `chief_complaint` top-level field

**Problem found in:** Transcript 06 (Mental Health), Transcript 02 (Chest Pain)

**What happened:**  
Complex cases produce dense subjective paragraphs. When displayed in the review UI, physicians had to scan the entire subjective section to understand the visit reason. This is especially bad for urgent cases.

**Fix:**  
Add `chief_complaint` as a short (1–2 sentence) top-level field extracted before the full subjective narrative. Example:  
`"chief_complaint": "Chest pain with jaw and left arm radiation, onset last evening."`

---

### Change 3: Explicit instruction to ignore non-physician speakers in multi-party transcripts

**Problem found in:** Transcript 04 (Pediatric — Nurse present)

**What happened:**  
The nurse's brief utterance ("Mrs. Rivera, the doctor is here") was harmlessly ignored, but the prompt gave no explicit instruction. In a noisier transcript (e.g., with nursing assessments, medical assistant vitals readings, or family members talking), the model might incorporate non-physician statements into clinical sections.

**Fix:**  
Add explicit instruction: "Only attribute clinical assessments and plans to the physician. Nursing or MA statements may be used for objective data (vitals) but should not appear in Assessment or Plan sections."

---

### Change 4: Mandatory `historian` field for pediatric/proxy cases

**Problem found in:** Transcript 04 (Pediatric)

**What happened:**  
The subjective contained "Historian: mother" buried mid-paragraph. For legal and clinical clarity, the historian identity should be a top-level structured field.

**Fix:**  
Add `"historian": "patient" | "parent/guardian" | "spouse" | "caregiver" | "other"` as a top-level field.

---

### Change 5: Strengthen JSON-only output enforcement

**Problem found in:** Not observed in test runs but anticipated.

**What happened:**  
V1 prompt says "Return ONLY valid JSON" but in manual adversarial testing (asking about ambiguous transcripts), GPT-4 sometimes prefixed output with "Here is the SOAP note:" before the JSON block, or added explanatory text after.

**Fix:**  
Reinforce with: "Your entire response MUST be a single raw JSON object. Do not include any text before or after the JSON. Do not use markdown code fences. Do not apologize or explain. If information is missing, use an empty string or empty array — never omit a key."

---

### Change 6: Add `follow_up` structured field

**Problem found in:** All transcripts

**What happened:**  
Follow-up instructions ("come back in 3 months", "return if fever >104°F", "follow up in 2 weeks") were buried in the plan text. The frontend needs to display this prominently and it may eventually auto-populate scheduling.

**Fix:**  
Add `"follow_up": { "timeframe": "...", "conditions": ["..."] }` as a structured top-level field.

---

## V1 → V2 Schema Diff

### V1 Schema
```json
{
  "subjective": "string",
  "objective": "string",
  "assessment": "string",
  "plan": "string",
  "medications": ["string"]
}
```

### V2 Schema
```json
{
  "chief_complaint": "string",
  "historian": "patient | parent/guardian | spouse | caregiver | other",
  "subjective": "string",
  "objective": "string",
  "assessment": "string",
  "plan": "string",
  "medications_new": [
    {
      "name": "string",
      "dose": "string",
      "route": "string",
      "frequency": "string",
      "duration": "string or null",
      "status": "new | increased | decreased | discontinued",
      "indication": "string"
    }
  ],
  "medications_existing": [
    {
      "name": "string",
      "dose": "string",
      "route": "string",
      "frequency": "string"
    }
  ],
  "follow_up": {
    "timeframe": "string",
    "conditions": ["string"]
  }
}
```

---

## Test Methodology

- 6 transcripts covering: routine checkup, acute emergency, complex chronic disease follow-up, pediatric with third-party historian, heavy crosstalk/filler words, psychiatric with sensitive content
- Each transcript run 3 times to check output consistency (temperature=0.2)
- Outputs validated programmatically against JSON schema (see `test_prompt.py`)
- Clinical accuracy reviewed manually against transcript ground truth
- Issues logged here and addressed iteratively

## Consistency Note (temperature=0.2)

Running each transcript 3× at temperature=0.2 showed <5% token-level variation across runs. The structure (keys, medication extraction, section boundaries) was identical across runs. Clinical phrasing varied slightly but remained accurate. This temperature is appropriate for production.
