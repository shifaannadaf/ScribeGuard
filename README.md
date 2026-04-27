<<<<<<< HEAD
# ScribeGuard

AI-powered clinical documentation assistant. Records doctor-patient consultations, transcribes them with OpenAI Whisper, adds speaker labels, extracts structured SOAP notes with GPT-4, and allows review and push to OpenMRS.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | FastAPI (Python) |
| Database | PostgreSQL (Docker) |
| AI | OpenAI Whisper-1 + GPT-4o-mini |
| EHR | OpenMRS REST API |

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

### 2. Start the database

```bash
docker compose up -d
```

This starts a PostgreSQL instance on `localhost:5432`.

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `backend/.env` and set your OpenAI API key:

```
DATABASE_URL=postgresql://scribeguard:scribeguard@localhost:5432/scribeguard
OPENAI_API_KEY=sk-...your-key-here
```

### 4. Install backend dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Seed the database

```bash
python seed.py
```

This creates all tables and inserts 5 sample encounters.

### 6. Start the backend

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API is now running at `http://localhost:8000`
Swagger UI at `http://localhost:8000/docs`

### 7. Install frontend dependencies

```bash
cd ../frontend
npm install
```

### 8. Start the frontend

```bash
npm run dev
```

App is now running at `http://localhost:5173`

---

## Usage

### Recording a consultation

1. Go to **Dashboard**
2. Click the **Mic** icon
3. Enter patient name and ID, click **Start Recording**
4. Speak the consultation, click **Stop Recording**
5. ScribeGuard will:
   - Transcribe the audio with Whisper
   - Format it with `Doctor:` / `Patient:` speaker labels
   - Extract medications, allergies, and diagnoses with GPT-4
6. You land on the **Note Detail** page to review and edit

### Reviewing notes (History)

- **Edit** (pencil) — edit transcript, medications, allergies, diagnoses
- **View** (eye) — read-only view
- **AI Assistant** (bot) — ask questions about the encounter in natural language
- **Approve** (checkmark) — mark as clinically reviewed
- **Revert** (undo) — move back to pending
- **Push to OpenMRS** (upload) — send to EHR (requires approved status)

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
| DELETE | `/encounters/{id}` | Delete encounter |
| POST | `/encounters/{id}/transcribe` | Transcribe audio file (Whisper) |
| POST | `/encounters/{id}/generate` | Extract SOAP data (GPT-4) |
| POST | `/encounters/{id}/format` | Add speaker labels (GPT-4) |
| POST | `/encounters/{id}/chat` | AI assistant chat |
| POST | `/encounters/{id}/push` | Push to OpenMRS |
| GET | `/encounters/stats` | Dashboard stats |
| GET | `/encounters/{id}/export/pdf` | Export as PDF |

Full interactive docs at `http://localhost:8000/docs`

---

## Project Structure

```
scribeguard/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, router registration
│   │   ├── config.py            # Settings (DATABASE_URL, OPENAI_API_KEY)
│   │   ├── whisper_service.py   # OpenAI Whisper transcription
│   │   ├── gpt_service.py       # GPT-4 note extraction, formatting, chat
│   │   ├── db/
│   │   │   └── database.py      # SQLAlchemy engine + session
│   │   ├── models/
│   │   │   └── models.py        # Encounter, Medication, Allergy, Diagnosis, AuditLog, ChatMessage
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
│   │       ├── Dashboard.tsx    # Record + stats
│   │       ├── History.tsx      # Encounter list
│   │       ├── NoteDetail.tsx   # Edit / view note
│   │       └── AiAssistant.tsx  # Chat UI
│   └── package.json
└── .gitignore
```
=======
# Radhika OpenMRS Setup Work
>>>>>>> origin/main
