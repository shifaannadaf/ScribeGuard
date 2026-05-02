# ScribeGuard

AI-powered clinical documentation assistant for outpatient workflows. ScribeGuard records or imports consultation transcripts, structures them into clinically useful note fields, supports review/approval workflows, and pushes validated data into OpenMRS.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | FastAPI (Python) |
| Database | PostgreSQL (Docker) |
| AI | OpenAI Whisper-1 + GPT-4o-mini |
| EHR | OpenMRS FHIR R4 + OpenMRS REST |

---

## Current Capabilities

- Capture encounters from live recording or import plain text transcripts
- Format raw dialogue with speaker labels (Doctor/Patient)
- Extract structured clinical data with GPT
- Review workflow with status controls: pending -> approved -> pushed
- Group history by patient with expandable visits
- View patient-level encounter timeline
- Push encounter data to OpenMRS (patient, encounter, vitals, diagnoses, meds, allergies)
- Avoid common OpenMRS duplicates (allergy/condition checks)
- Use AI Assistant with both current encounter context and available OpenMRS history

---

## Prerequisites

- [Node.js](https://nodejs.org/) 18+
- [Python](https://www.python.org/) 3.11+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- An [OpenAI API key](https://platform.openai.com/api-keys)

---

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd scribeguard
```

### 2. Configure environment variables

Create a backend env file:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set your values:

```env
# App
DATABASE_URL=postgresql://scribeguard:scribeguard@localhost:5432/scribeguard
OPENAI_API_KEY=sk-...your-key-here

# OpenMRS
FHIR_SERVER=http://localhost:8080/openmrs/ws/fhir2/R4
OPENMRS_USER=Admin
OPENMRS_PASSWORD=Admin123
```

### 3. Start backend + database with Docker

```bash
docker compose up -d
```

This starts:

- PostgreSQL on `localhost:5432`
- FastAPI backend on `localhost:8000`

### 4. (Optional) Seed the database

If you want sample local data:

```bash
cd backend
python seed.py
```

### 5. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173` (or `5174` if `5173` is occupied).

### 6. Verify services

- API health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

---

## OpenMRS Notes

- ScribeGuard uses FHIR R4 endpoints for most resources.
- Diagnoses/conditions use an OpenMRS REST flow to ensure proper concept mapping and display.
- Encounter push requires approved status.
- If you need to re-test a pushed encounter, use the unpush endpoint to move it back to approved.

---

## Usage

### Record or import a consultation

1. Open **Dashboard**.
2. Create/select patient context.
3. Either:
   - Record audio with the mic, or
   - Import a `.txt` transcript file.
4. Run formatting/extraction pipeline.
5. Review in **Note Detail**.
6. Approve, then push to OpenMRS.

### Review and push workflow

- **Edit**: Update transcript and extracted fields
- **View**: Read-only clinical review
- **AI Assistant**: Ask clinical/contextual questions
- **Approve**: Mark reviewed and ready for push
- **Revert**: Move approved back to pending
- **Push to OpenMRS**: Send to EHR (approved only)
- **Unpush**: Move pushed back to approved for retesting

### History and patient drill-down

- **History** page groups encounters by patient.
- Multi-visit patients can be expanded/collapsed.
- Use patient timeline view for all visits for one patient.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/encounters` | List encounters (filter by status, search) |
| POST | `/encounters` | Create encounter |
| GET | `/encounters/{id}` | Get encounter detail |
| PATCH | `/encounters/{id}` | Update transcript / structured data |
| PATCH | `/encounters/{id}/approve` | Approve encounter |
| PATCH | `/encounters/{id}/revert` | Revert to pending |
| PATCH | `/encounters/{id}/unpush` | Move pushed -> approved |
| DELETE | `/encounters/{id}` | Delete encounter |
| POST | `/encounters/{id}/transcribe` | Transcribe audio file (Whisper) |
| POST | `/encounters/{id}/generate` | Extract SOAP data (GPT-4) |
| POST | `/encounters/{id}/format` | Add speaker labels (GPT-4) |
| POST | `/encounters/{id}/chat` | AI assistant chat |
| POST | `/encounters/{id}/push` | Push to OpenMRS |
| GET | `/encounters/patient-status?patient_id=...` | New vs returning patient check |
| GET | `/encounters/stats` | Dashboard stats |
| GET | `/encounters/{id}/export/pdf` | Export as PDF |
| GET | `/health` | Health check |

Full interactive docs at `http://localhost:8000/docs`

---

## Frontend Routes

| Route | Purpose |
|------|---------|
| `/dashboard` | Record/import and run extraction pipeline |
| `/history` | Encounter history grouped by patient |
| `/notes/:id` | Review and edit one encounter |
| `/notes/:id/ai` | AI assistant for encounter |
| `/patients` | OpenMRS patient search/list |
| `/patients/encounters/:patientId` | Patient timeline across visits |
| `/patients/:uuid` | OpenMRS patient profile |

---

## Project Structure

```
scribeguard/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, router registration
│   │   ├── config.py            # App settings
│   │   ├── whisper_service.py   # OpenAI Whisper transcription
│   │   ├── gpt_service.py       # GPT extraction/format/chat
│   │   ├── db/
│   │   │   └── database.py      # SQLAlchemy engine + session
│   │   ├── models/
│   │   │   └── models.py        # Encounter + related clinical models
│   │   ├── openmrs/             # OpenMRS FHIR/REST integration layer
│   │   ├── routers/
│   │   │   ├── encounters.py    # CRUD + stats
│   │   │   ├── pipeline.py      # transcribe / format / generate
│   │   │   ├── chat.py          # AI assistant
│   │   │   ├── openmrs.py       # OpenMRS push
│   │   │   └── export.py        # PDF export
│   │   └── schemas/
│   │       ├── encounter.py     # Pydantic schemas
│   │       └── misc.py          # Chat, pipeline schemas
│   ├── seed.py                  # Seed 5 mock encounters
│   ├── docker-compose.yml       # PostgreSQL container
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts        # Base fetch wrapper
│   │   │   └── encounters.ts    # All API calls + types
│   │   ├── components/
│   │   │   ├── AppLayout.tsx    # Sidebar + outlet
│   │   │   └── Sidebar.tsx      # Nav
│   │   └── pages/
│   │       ├── Login.tsx
│   │       ├── Dashboard.tsx    # Record/import + stats
│   │       ├── History.tsx      # Patient-grouped encounter history
│   │       ├── NoteDetail.tsx   # Edit / view note
│   │       └── AiAssistant.tsx  # Chat UI
│   └── package.json
└── .gitignore
```

---

## Troubleshooting

- If OpenMRS push fails with auth errors, verify `OPENMRS_USER` and `OPENMRS_PASSWORD`.
- If frontend cannot reach backend, confirm API is up at `http://localhost:8000/health`.
- If CORS issues appear, ensure frontend is running on `5173` or `5174`.
- If a pushed encounter must be resent, call `/encounters/{id}/unpush` first.
