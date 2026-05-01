# ScribeGuard — Agentic AI Architecture

ScribeGuard is implemented as a **multi-agent clinical workflow system**. Every
major responsibility along the encounter pipeline is owned by a dedicated,
autonomous agent. A central **orchestrator** coordinates them, persists
each agent run, advances pipeline state, and emits a durable audit trail.

This document is the engineering reference for that architecture.

---

## 1. System overview

```
                ┌──────────────────────┐
                │  React Workspace UI  │
                │  (physician-facing)  │
                └──────────┬───────────┘
                           │   /encounters, /agents, /audit
                           ▼
                ┌──────────────────────┐
                │   FastAPI HTTP API   │
                │  (routers, schemas)  │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────────────────────────┐
                │        Agent Orchestrator                │
                │  (retries, persistence, audit emission)  │
                └──────────┬───────────────────────────────┘
                           │
   ┌────────┬──────────────┼──────────────┬──────────────┬───────────────┐
   ▼        ▼              ▼              ▼              ▼               ▼
 Intake   Transcription  Note Gen.    Med Extract.   Physician Review   OpenMRS
 Agent    Agent          Agent        Agent          Agent              Integration
                                                                        Agent
                                                                          │
                                                       ┌──────────────────┼──────────────────┐
                                                       ▼                  ▼                  ▼
                                                    Auth Sub        Patient Ctx Sub      Mapper / Writer / Verifier
                           │
                           ▼
                ┌──────────────────────────────────────────┐
                │         PostgreSQL (durable state)       │
                │  encounters, transcripts, soap_notes,    │
                │  medications, physician_edits,           │
                │  submission_records, agent_runs,         │
                │  audit_events                            │
                └──────────────────────────────────────────┘
                           │
                           ▼
                ┌──────────────────────────────────────────┐
                │       Audit & Traceability Agent         │
                │  (queryable, exportable timeline view)   │
                └──────────────────────────────────────────┘
```

---

## 2. The 7 specialized agents

Every agent is a subclass of `app.agents.base.Agent` with a uniform contract:

```python
class Agent(abc.ABC, Generic[T]):
    name: str       # e.g. "TranscriptionAgent"
    version: str    # semver string
    description: str

    async def run(self, ctx: AgentContext) -> AgentResult[T]:
        ...
```

`AgentContext` bundles the SQLAlchemy session, the `Encounter` being processed,
the actor, an arbitrary `payload` dict, and lazy repository accessors
(`ctx.transcripts`, `ctx.soap_notes`, …). Cross-cutting concerns (retry,
agent-run persistence, state advancement, audit emission) live in the
orchestrator — agents stay focused on their single responsibility.

| # | Agent | File | Purpose |
|---|-------|------|---------|
| 1 | `EncounterIntakeAgent` | `app/agents/intake.py` | Validate audio (mime, size, integrity), persist to `AudioStorage`, set encounter metadata, emit intake audit event. |
| 2 | `TranscriptionAgent` | `app/agents/transcription.py` | Read audio bytes, call Whisper, normalize whitespace/casing, score quality, persist `Transcript` artifact. |
| 3 | `ClinicalNoteGenerationAgent` | `app/agents/note_generation.py` | Run engineered SOAP prompt against GPT-4 family, produce strict JSON, persist a versioned `SoapNote`, mark low-confidence sections. |
| 4 | `MedicationExtractionAgent` | `app/agents/medication_extraction.py` | Parse SOAP Plan into structured drug entities (name/dose/route/frequency/duration/indication/confidence). |
| 5 | `PhysicianReviewAgent` | `app/agents/physician_review.py` | Manage `open_review`, `edit`, `approve`, `revert` actions. Records every section edit and explicit approval. **No AI output is committed without an explicit approve action through this agent.** |
| 6 | `OpenMRSIntegrationAgent` | `app/agents/openmrs/integration.py` | Composite system-of-record agent. Delegates to focused sub-agents: `OpenMRSAuthAgent`, `OpenMRSPatientContextAgent`, `OpenMRSEncounterMapperAgent`, `OpenMRSNoteWriterAgent`, `OpenMRSSubmissionVerifierAgent`. Writes a `SubmissionRecord` for every attempt. |
| 7 | `AuditTraceabilityAgent` | `app/agents/audit.py` | Aggregates the audit-event + agent-run streams into a single chronological timeline with per-agent rollups. Exposed at `/encounters/{id}/audit/timeline`. |

The OpenMRS sub-agents (`auth`, `patient_context`, `encounter_mapper`,
`note_writer`, `verifier`) are independently importable and individually
testable. They honor `OPENMRS_SIMULATE=true` so demos work without a live
sandbox.

---

## 3. The orchestrator

`app/orchestrator/orchestrator.py` exposes two public methods:

- `run_agent(name, encounter, *, actor, payload)` — runs one agent with
  retries, persists an `AgentRun` row, emits audit events, advances state on
  success, raises on failure.
- `run_pipeline(encounter, actor)` — runs the auto-pipeline:
  Intake → Transcription → SOAP → Medication. Stops short of physician
  review (manual gate) and OpenMRS submission (only after explicit approval).

Per-stage transitions are committed atomically: a partial pipeline run is
fully durable, so a later call resumes from the last completed stage.

The orchestrator is the **only** code that mutates `encounter.processing_stage`
across stage boundaries. Individual agents may set transient stages
(e.g. `transcribing`) but cross-stage transitions are orchestrator-driven.

Retries: configurable via `AGENT_MAX_RETRIES`/`AGENT_RETRY_BASE_DELAY_SECONDS`.
`AgentValidationError` is non-retriable; `AgentExecutionError` and unexpected
exceptions are retried with linear backoff.

---

## 4. State machine

`Encounter.status` is the user-visible lifecycle (`pending` / `approved` /
`pushed` / `failed`). `Encounter.processing_stage` is the fine-grained
agentic state used by the orchestrator and surfaced live in the UI:

```
created → audio_received → transcribing → transcribed →
generating_soap → soap_drafted → extracting_meds →
ready_for_review → in_review → approved →
submitting → submitted

(failed at any point)
```

The frontend's `AgentTimeline` renders this directly so the physician can
see exactly where the system is.

---

## 5. Persistence model

| Table | Owner | Purpose |
|-------|-------|---------|
| `encounters`           | EncounterIntakeAgent | Root aggregate, audio metadata, status + processing_stage |
| `transcripts`          | TranscriptionAgent | Whisper output + cleaned text + quality signals |
| `soap_notes`           | ClinicalNoteGenerationAgent / PhysicianReviewAgent | Versioned SOAP draft (`is_current` flag), low-confidence flags, `status` |
| `medications`          | MedicationExtractionAgent | Structured drug entities; `confidence` per row |
| `physician_edits`      | PhysicianReviewAgent | Per-section edit log (original vs edited) |
| `physician_approvals`  | PhysicianReviewAgent | Approval records with actor + comments + edits-made counter |
| `submission_records`   | OpenMRSIntegrationAgent | OpenMRS write attempts + UUIDs returned + retries |
| `agent_runs`           | Orchestrator | One row per agent invocation: status, attempt, durations, error context |
| `audit_events`         | All agents (writes); AuditTraceabilityAgent (reads) | High-level clinical/business event stream |

Migrations are managed by Alembic (`alembic/versions/0001_initial_agentic_schema.py`).
For local first-run convenience, `python create_tables.py` mirrors the
migration via `Base.metadata.create_all`.

---

## 6. HTTP API

All routes are documented under `/docs` (Swagger UI). Major surfaces:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/encounters` | Create encounter |
| POST | `/encounters/{id}/intake?auto_run=true` | Upload audio + auto-run pipeline |
| POST | `/encounters/{id}/run` | Run the full agent pipeline |
| POST | `/encounters/{id}/transcribe` | Run TranscriptionAgent |
| POST | `/encounters/{id}/generate-soap` | Run note + medication agents |
| POST | `/encounters/{id}/extract-medications` | Run MedicationExtractionAgent |
| GET  | `/encounters/{id}/pipeline` | Pipeline status + agent runs |
| PATCH| `/encounters/{id}/review/edit` | Physician edits a draft |
| POST | `/encounters/{id}/review/approve` | Explicit physician approval |
| POST | `/encounters/{id}/review/revert` | Revert approval |
| POST | `/encounters/{id}/submit` | OpenMRSIntegrationAgent submission |
| GET  | `/encounters/{id}/audit` | Audit event list |
| GET  | `/encounters/{id}/audit/timeline` | Aggregated timeline (Audit Agent) |
| GET  | `/agents` | Registry list |
| GET  | `/openmrs/...` | Direct FHIR R4 admin endpoints |

---

## 7. Frontend

- `Dashboard` — record audio (MediaRecorder), agent registry preview, pipeline progression visualization.
- `EncounterWorkspace` — agent-pipeline timeline, SOAP review/edit (with low-confidence highlighting and revert-section), medication panel, agent-run table, audit trail. Auto-polls while a stage is in flight.
- `History` — searchable list of encounters with their pipeline stage and submission status.
- Shared components: `AgentTimeline`, `SoapEditor`, `MedicationPanel`.

The frontend is unopinionated about the backend implementation — it consumes
the HTTP API documented above. The full physician-in-the-loop guarantee
(no submission without explicit approval) is enforced server-side in the
`PhysicianReviewAgent` and `OpenMRSIntegrationAgent`.

---

## 8. Configuration

All runtime config flows through `app/config.py:Settings` (Pydantic v2). Key
keys:

- `OPENAI_API_KEY` — required for live Whisper + GPT calls.
- `WHISPER_MODEL`, `SOAP_MODEL`, `MEDICATION_MODEL` — model overrides.
- `FHIR_SERVER`, `OPENMRS_USER`, `OPENMRS_PASSWORD` — OpenMRS sandbox.
- `OPENMRS_SIMULATE` — when `true` (default), the OpenMRS Integration Agent
  simulates writes with stable fake UUIDs so demos never need a live sandbox.
- `AGENT_MAX_RETRIES`, `AGENT_RETRY_BASE_DELAY_SECONDS`, `AGENT_AUDIT_ENABLED`.
- `AUDIO_STORAGE_DIR` — local audio store.

---

## 9. Future agent extension points

ScribeGuard's agent layer is designed for the Layer 2 / Layer 3 work in the
roadmap. Concrete extension points:

| Future capability | Hook |
|-------------------|------|
| **Layer 2 — Prescription Reconciliation Agent** | Read existing `medications` rows + OpenMRS `MedicationRequest` resources via `app/openmrs/medication.py`. Add `ReconciliationAgent` that runs *after* `MedicationExtractionAgent` and emits `reconciliation_findings` rows. |
| **Layer 3 — Dosage Anomaly Agent** | Take the reconciled medication list and validate against OpenFDA + DrugBank. Implement as `DosageAnomalyAgent` invoked after Layer 2. |
| **e-prescribing** | Add an e-Rx submission sub-agent under `app/agents/openmrs/`, mirroring the existing `OpenMRSNoteWriterAgent`. |
| **Patient reminders** | Subscribe a new agent to the `audit_events` stream, consuming `review.approved` events. |
| **HIPAA-grade audit shipping** | Add an exporter agent that mirrors `audit_events` to immutable storage. |
| **Custom model fine-tuning** | Replace the `OpenAIClient` with an alternative `LLMClient` implementation; agent code is unchanged. |

Adding a new agent is a four-step process:

1. Create `app/agents/<name>.py` subclassing `Agent`.
2. Register it in `app/orchestrator/registry.py:build_default_registry`.
3. Optionally add a router that calls `orchestrator.run_agent(...)`.
4. (Optional) Persist new artifact tables under `app/models/` + a new
   Alembic migration.

No changes are required to the orchestrator, retry policy, or audit code:
those concerns are agent-agnostic.

---

## 10. Engineering rationale

- **Why dedicated agents instead of a single pipeline function?** Clinical
  workflows have heterogeneous failure modes — Whisper rate-limits, GPT JSON
  parse errors, OpenMRS auth errors, physician override conflicts. Wrapping
  each as a typed `Agent` with its own input contract makes those failure
  modes addressable individually and keeps retry boundaries clean.
- **Why repositories?** So agents never see SQLAlchemy directly and the data
  layer can be swapped (e.g. for unit-test fakes) without touching agents.
- **Why an explicit orchestrator?** It is the single source of truth for
  state transitions and observability. Without it, audit gaps appear when
  agents partially succeed.
- **Why versioned SOAP notes?** Because regenerating a draft after a physician
  has started editing must not blow away their work — the previous version is
  marked `superseded`, the new one becomes `is_current=true`.
- **Why split the OpenMRS integration into sub-agents?** So the failure
  reason (auth vs. mapping vs. write vs. verify) is clear in the audit
  trail, and so each step can be retried independently in future iterations.
