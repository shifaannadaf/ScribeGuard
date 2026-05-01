# ScribeGuard

ScribeGuard is an **agentic AI clinical-documentation platform** integrated with
**OpenMRS**. Specialized autonomous agents collaborate end-to-end to convert a
recorded doctor-patient encounter into a physician-reviewed, FHIR-aligned
clinical record that is written back into the patient's OpenMRS chart —
medication requests, allergies, conditions, vital-sign observations, and the
clinical note itself, each in the correct FHIR resource.

The architecture is described in detail in [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## What runs end-to-end

```
   Web mic                                                      OpenMRS
  ┌──────┐  audio   ┌─────────────┐ pipeline  ┌─────────────┐  FHIR R4
  │React │ ───────▶ │  FastAPI +  │ ────────▶ │  agents +   │ ────────▶
  │ UI   │          │ orchestrator│           │  OpenAI     │  Encounter,
  └──────┘ review/  └─────────────┘ persist   └─────────────┘  Observation,
           approve            ▲                       │        AllergyIntolerance,
                              │                       ▼        Condition,
                       ┌────────────────────────────────┐      MedicationRequest
                       │       PostgreSQL audit         │
                       │  encounters, transcripts,      │
                       │  soap_notes, medications,      │
                       │  allergies, conditions,        │
                       │  vital_signs, follow_ups,      │
                       │  patient_contexts,             │
                       │  agent_runs, audit_events      │
                       └────────────────────────────────┘
```

**Seven specialized agents** drive the workflow:

1. **EncounterIntakeAgent** — validates audio, persists it, snapshots the patient's existing OpenMRS chart so the reviewer sees real chart context.
2. **TranscriptionAgent** — Whisper + cleanup + quality flags.
3. **ClinicalNoteGenerationAgent** — versioned SOAP note from a GPT-4 family model under an engineered, version-pinned prompt.
4. **ClinicalEntityExtractionAgent** — classifies the SOAP note + transcript into FHIR-aligned entities: medications, allergies, conditions, vital signs, follow-ups (each with ICD-10/SNOMED where applicable).
5. **PhysicianReviewAgent** — physician-in-the-loop edit/approve. **Nothing is committed without explicit physician approval.**
6. **OpenMRSIntegrationAgent** — composite: authenticate → resolve patient → map → write Encounter, clinical-note Observation, vital-sign Observations, AllergyIntolerance, Condition, MedicationRequest → verify.
7. **AuditTraceabilityAgent** — durable agent-run + clinical-event audit trail, exposed as a queryable timeline.

The orchestrator (`app/orchestrator/orchestrator.py`) is the single piece of
code that mutates pipeline state, persists every `agent_run`, and emits
`audit_events`. Retries are configurable via `AGENT_MAX_RETRIES` /
`AGENT_RETRY_BASE_DELAY_SECONDS`.

---

## Stack

| Layer       | Technology                                   |
| ----------- | -------------------------------------------- |
| Frontend    | React 19 + TypeScript + Vite                 |
| Backend     | FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic |
| Database    | PostgreSQL                                   |
| AI          | OpenAI Whisper + GPT-4 family                |
| EHR         | OpenMRS REST + FHIR R4                       |

---

## Setup

### 1. Database
```bash
docker compose up -d              # PostgreSQL on :5432
```

### 2. OpenMRS sandbox
Bring up an OpenMRS Reference Application (FHIR2 module) on
`http://localhost:8080/openmrs/ws/fhir2/R4`. Then in `backend/.env`:

```
DATABASE_URL=postgresql://scribeguard:scribeguard@localhost:5432/scribeguard
OPENAI_API_KEY=sk-...
FHIR_SERVER=http://localhost:8080/openmrs/ws/fhir2/R4
OPENMRS_USER=Admin
OPENMRS_PASSWORD=Admin123
OPENMRS_SIMULATE=false
```

`OPENMRS_SIMULATE=false` is the production default — the OpenMRS
Integration Agent makes real FHIR calls. Set it to `true` only for CI /
smoke tests where no sandbox is reachable.

### 3. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head               # or: python create_tables.py
uvicorn app.main:app --reload --port 8000
```

Swagger UI: `http://localhost:8000/docs`

### 4. Frontend
```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

---

## Usage

1. **Dashboard** — start a new encounter. The browser MediaRecorder captures audio. On stop, the file is uploaded and the orchestrator runs the full agent pipeline.
2. **Encounter Workspace** — the physician sees:
   - **Pipeline timeline** — live agent execution status
   - **SOAP Review** — editable Subjective / Objective / Assessment / Plan with low-confidence highlighting; **explicit Approve & Lock** required
   - **Medications**, **Allergies**, **Conditions**, **Vital Signs**, **Follow-ups** — each in its own panel mirroring the matching FHIR resource
   - **Transcript** — Whisper output with quality signals
   - **Agents** — every agent run with attempt, duration, error context
   - **Audit** — the full clinical/business event log
   - Right-side **OpenMRS chart context** sidebar — demographics, active medications, allergies, conditions, recent encounters, **all fetched live from OpenMRS**
3. After approval, **Submit to OpenMRS** writes back: clinical-note Observation, vital-sign Observations (CIEL-coded), AllergyIntolerance, Condition (ICD-10 + SNOMED), MedicationRequest. Each write returns a UUID stored on the entity row.

No demo data is seeded — every entity in the UI comes from a real audio
recording, a real Whisper/GPT call, or a real OpenMRS read.

---

## Repository layout

```
backend/
  app/
    agents/                   # 7 specialized agents (+ OpenMRS sub-agents)
      intake.py
      transcription.py
      note_generation.py
      clinical_extraction.py
      physician_review.py
      openmrs/                # auth, patient_context, encounter_mapper, note_writer, verifier, integration
      audit.py
      prompts/                # version-pinned engineered prompts
    orchestrator/             # AgentOrchestrator + AgentRegistry
    repositories/             # data access boundary
    clients/                  # OpenAI wrapper
    openmrs/                  # FHIR R4 HTTP client (kept from baseline)
    models/                   # SQLAlchemy models, one per aggregate
    schemas/                  # Pydantic v2 API schemas
    routers/                  # FastAPI HTTP routes
    main.py
  alembic/                    # migrations 0001 + 0002
frontend/
  src/
    pages/                    # Login, Dashboard, History, EncounterWorkspace
    components/               # AgentTimeline, SoapEditor, MedicationPanel,
                              # EntityPanels, PatientContextPanel
    api/                      # Typed API client
ARCHITECTURE.md
```

See `ARCHITECTURE.md` for the deep dive on agent contracts, state machine,
extension points (Layer 2 prescription reconciliation, Layer 3 dosage
anomaly detection, e-prescribing, etc.) and engineering rationale.
