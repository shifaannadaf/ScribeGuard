# SOAP Note Prompt Engineering — Test Suite

This folder contains all artifacts for Sprint 1 GPT-4 prompt engineering work.

## Structure

```
test/
├── prompts/
│   ├── system_prompt_v1.md     # Initial prompt
│   └── system_prompt_v2.md     # Refined production prompt ← USE THIS
│
├── transcripts/
│   ├── transcript_01_routine_checkup.txt     # Clean, straightforward
│   ├── transcript_02_chest_pain.txt          # Urgent, emotional patient
│   ├── transcript_03_diabetes_followup.txt   # Complex multi-med chronic disease
│   ├── transcript_04_pediatric_fever.txt     # 3rd-party historian, child present
│   ├── transcript_05_messy_crosstalk.txt     # Heavy filler words, interruptions ★
│   └── transcript_06_mental_health.txt       # Sensitive content, dose change
│
├── outputs/
│   ├── v1/                     # Raw GPT-4 outputs from v1 prompt
│   └── v2/                     # Raw GPT-4 outputs from v2 prompt
│
├── results/
│   ├── test_results_v1.md      # Analysis of v1 test run
│   ├── test_results_v2.md      # Analysis of v2 test run
│   └── refinement_log.md       # Issue-by-issue explanation of all v1→v2 changes
│
└── test_prompt.py              # Test runner — runs all transcripts against a prompt version
```

## Running Tests

```bash
export OPENAI_API_KEY=sk-...

# Test v1 prompt
python test/test_prompt.py --version v1

# Test v2 prompt (production)
python test/test_prompt.py --version v2

# Use a specific model
python test/test_prompt.py --version v2 --model gpt-4o
```

## Production Config

| Setting | Value |
|---------|-------|
| Prompt file | `test/prompts/system_prompt_v2.md` |
| Model | `gpt-4o` |
| Temperature | `0.2` |
| Max tokens | `1800` |

## Output Schema (V2)

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
      "duration": "string | null",
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

## Test Coverage Summary

| Test | Purpose |
|------|---------|
| T01 Routine Checkup | Baseline — clean transcript, straightforward note |
| T02 Chest Pain | Urgent presentation, emotional patient, existing medication separation |
| T03 Diabetes Follow-up | Complex chronic disease, multiple meds, dose adherence discussion |
| T04 Pediatric Fever | Third-party historian, child speech, pediatric dosing math |
| T05 Messy Crosstalk ★ | Primary robustness test — filler words, interruptions, incomplete sentences |
| T06 Mental Health | Sensitive content, passive SI, dose change tracking |
