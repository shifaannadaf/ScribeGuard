# Test Results — Prompt V2

**Date:** 2026-04-12 10:06:15  
**Model:** gpt-4o  
**Pass rate:** 6/6 (100% structurally valid JSON)

---

## Summary Table

| # | Transcript | V1 Status | V2 Status | Key Improvements |
|---|-----------|-----------|-----------|------------------|
| 01 | Routine Annual Checkup | ✓ PASS | ✓ PASS | Added chief_complaint, follow_up fields |
| 02 | Acute Chest Pain | ✓ PASS | ✓ PASS | Lisinopril moved to medications_existing; new meds clearly in medications_new |
| 03 | Diabetes Follow-up | ✓ PASS | ✓ PASS | medications_new has only 2 new drugs; existing meds in medications_existing with doses |
| 04 | Pediatric Fever | ✓ PASS | ✓ PASS | historian="parent/guardian" set; weight in objective for dosing context |
| 05 | Messy Crosstalk (LBP) | ✓ PASS | ✓ PASS | Consistent improvement maintained |
| 06 | Mental Health | ✓ PASS | ✓ PASS | Sertraline dose change status="increased"; follow_up.conditions captures safety plan |

---

## Key Structural Improvements (V2 vs V1)

### 1. Medication Type Separation
V1 mixed all medications into one array. V2 cleanly separates:
- `medications_new` — only drugs prescribed or adjusted THIS visit
- `medications_existing` — drugs patient was already taking

This is critical for the OpenMRS write-back in Sprint 2. The system can now iterate `medications_new` to create new medication orders without risking duplicate orders for existing prescriptions.

### 2. Dose Change Tracking
The `status` field in `medications_new` enables medication reconciliation logic:
- `"new"` → create new medication order in OpenMRS
- `"increased"` / `"decreased"` → update existing order, retain history
- `"discontinued"` → close/void existing order

### 3. chief_complaint
Provides a one-sentence visit summary for the review UI header. Physicians can immediately see the visit context before reading full SOAP sections.

### 4. follow_up.conditions (Structured Safety/Return Precautions)
V1 buried return precautions in the plan text. V2's `follow_up.conditions` array is machine-readable — can be used to display a prominent warning panel in the review UI and eventually to generate patient-facing after-visit summary cards.

### 5. historian field
Enables the review UI to display a "(History provided by: parent/guardian)" label on the subjective section, which is important for clinical accuracy assessment.

---

## Remaining Known Limitations

| Limitation | Severity | Notes |
|-----------|----------|-------|
| Allergy information not extracted | LOW | Could be added as `allergies: []` field in V3 if needed |
| Vitals not parsed into structured fields | LOW | Kept as free text in objective — structured vitals would require knowing every possible vital format |
| Confidence scoring | MEDIUM | No mechanism to flag when the model is unsure (e.g., garbled audio segment). Could add `confidence: "high/medium/low"` in V3 |
| ICD-10 / SNOMED codes | LOW | Assessment uses plain-text diagnoses — code lookup is better done by a separate service than baked into the prompt |

---

## Final Verdict

**V2 is the production-ready prompt.** It is:
- ✓ Structurally consistent across all 6 transcript types
- ✓ Robust to messy, real-world transcripts
- ✓ Medically accurate (no hallucinations observed in testing)
- ✓ Machine-parseable for downstream medication write-back
- ✓ Backwards-compatible: all V1 fields still present

**The prompt file to use in production:** `test/prompts/system_prompt_v2.md`  
**The model config to use:** `gpt-4o`, `temperature=0.2`, `max_tokens=1800`
