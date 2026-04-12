# Test Results — Prompt V1

**Date:** 2026-04-12 09:20:47  
**Model:** gpt-4o  
**Pass rate:** 6/6 (100% structurally valid JSON)

---

## Summary Table

| # | Transcript | Status | Key Issues |
|---|-----------|--------|------------|
| 01 | Routine Annual Checkup | ✓ PASS | None |
| 02 | Acute Chest Pain | ✓ PASS | Existing meds mixed with new prescriptions in medications[] |
| 03 | Diabetes Follow-up | ✓ PASS | new vs continued meds not structurally differentiated |
| 04 | Pediatric Fever | ✓ PASS | Parent-reported dose vs physician-prescribed dose indistinguishable |
| 05 | Messy Crosstalk (LBP) | ✓ PASS | None — robustness test passed cleanly |
| 06 | Mental Health | ✓ PASS | Dose change not structured; no chief_complaint field |

---

## Transcript 01 — Routine Annual Checkup
**File:** `transcript_01_routine_checkup.txt`  
**Status:** ✓ PASS  
**Extracted medications:**
- Metformin 500 mg oral twice daily with meals
- Atorvastatin 20 mg oral once daily at bedtime

**Notes:** Clean, well-structured output. Clinical language conversion from casual speech is accurate. All four SOAP sections populated correctly with appropriate content. Medications correctly formatted with dose, route, and frequency.

---

## Transcript 02 — Acute Chest Pain
**File:** `transcript_02_chest_pain.txt`  
**Status:** ✓ PASS  
**Extracted medications:**
- Aspirin 325 mg oral once (chew immediately)
- Heparin IV (dose per protocol)
- Nitroglycerin sublingual PRN chest pain
- Lisinopril (existing, dose not specified)

**Notes:** Clinical reasoning correct. ACS correctly identified. **Issue identified:** Lisinopril is a pre-existing medication mentioned incidentally — not a new prescription. The v1 prompt doesn't distinguish `medications_new` from `medications_existing`. This could cause the downstream write-back to attempt to re-prescribe a drug the patient is already on.

---

## Transcript 03 — Diabetes Follow-up
**File:** `transcript_03_diabetes_followup.txt`  
**Status:** ✓ PASS  
**Extracted medications:**
- Empagliflozin 10 mg oral once daily
- Metformin 1000 mg oral twice daily (continued)
- Glipizide 5 mg oral twice daily (continued)
- Gabapentin 300 mg oral once daily at bedtime

**Notes:** Complex multi-medication case handled well. **Issue identified:** The label "(continued)" appears inconsistently — Gabapentin is new but unlabeled, while Metformin and Glipizide have "(continued)". This inconsistency needs to be resolved into a structured `status` field per medication in v2.

---

## Transcript 04 — Pediatric Fever
**File:** `transcript_04_pediatric_fever.txt`  
**Status:** ✓ PASS  
**Extracted medications:**
- Amoxicillin oral suspension 400 mg/5 mL — 5 mL (250 mg) orally twice daily for 10 days
- Acetaminophen oral — dose per weight (1.5 tsp per mother's report) as needed for fever
- Ibuprofen oral suspension 100 mg/5 mL — 7 mL orally every 6–8 hours with food as needed

**Notes:** Child interjections correctly ignored. Third-party historian (mother) correctly noted. Confusing suspension math (400 mg/5 mL prescribed but actual dose is 250 mg) correctly resolved. **Issue identified:** Acetaminophen dose is labeled as "mother's report" — the prompt has no mechanism to flag physician-confirmed vs patient-reported dosing.

---

## Transcript 05 — Messy Crosstalk (Lower Back Pain)
**File:** `transcript_05_messy_crosstalk.txt`  
**Status:** ✓ PASS  
**Extracted medications:**
- Naproxen 500 mg oral twice daily with food
- Cyclobenzaprine 5 mg oral once daily at bedtime

**Notes:** This is the key robustness test. Heavy filler words ("uh", "um", "like", "you know"), interrupted sentences, and topic jumping all handled correctly. Output is clean and professional. No hallucinations. The patient's occupation (delivery driver, 8–10 hrs/day driving) was correctly retained as clinically relevant context. **PASS — prompt is robust to messy real-world transcripts.**

---

## Transcript 06 — Mental Health / Psychiatric Follow-up
**File:** `transcript_06_mental_health.txt`  
**Status:** ✓ PASS  
**Extracted medications:**
- Sertraline 150 mg oral once daily (increased from 100 mg)
- Bupropion XL 150 mg oral once daily in morning
- Lorazepam 0.5 mg oral as needed (max 3x/week)

**Notes:** Sensitive content (passive SI) handled appropriately with clinical nuance preserved. Safety plan correctly placed in Plan section. **Issue identified:** Dose change (sertraline 100→150 mg) is embedded in free text string — not machine-parseable. Downstream medication reconciliation needs to know the previous dose. **Issue identified:** For complex psychiatric cases, the subjective section becomes a single dense paragraph. A `chief_complaint` top-level field would improve structure and readability.

---

## Issues to Address in V2

| Priority | Issue | Fix |
|----------|-------|-----|
| HIGH | medications[] mixes new prescriptions with existing/pre-existing | Split into `medications_new` (newly prescribed this visit) and `medications_existing` (mentioned as current) |
| HIGH | No structured dose-change representation | Add `previous_dose` field or `status` field per medication: "new" / "continued" / "increased" / "decreased" / "discontinued" |
| MEDIUM | No `chief_complaint` field | Add top-level `chief_complaint` string (1 sentence) |
| MEDIUM | Parent/patient-reported doses not flagged | Add `source` field to medication entries: "physician_prescribed" / "patient_reported" |
| LOW | Inconsistent "(continued)" labeling in free text | Eliminated by v2 structured approach |
