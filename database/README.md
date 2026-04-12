# Database Setup — Sprint 1

This folder contains the PostgreSQL schema and SQLAlchemy models for the SOAP Note application.

---

##  Files

| File | Description |
|------|-------------|
| `database.py` | DB engine, session setup, and `get_db()` dependency for FastAPI |
| `models.py` | SQLAlchemy ORM models for all 4 tables |
| `schema.sql` | Raw SQL to manually create tables (for reference or direct use) |

---

##  Tables

| Table | Purpose |
|-------|---------|
| `transcripts` | Stores audio filename and raw Whisper transcript |
| `generated_notes` | Stores GPT-4 SOAP note sections (S, O, A, P) per transcript |
| `physician_edits` | Tracks every edit a physician makes to any SOAP section |
| `audit_log` | Records all actions taken on notes (generated, edited, approved) |

---

##  Prerequisites

- Python 3.9+
- PostgreSQL installed and running
- Install dependencies:

```bash
pip install sqlalchemy psycopg2-binary
```

---

##  Setup Instructions

### 1. Create the PostgreSQL database

```bash
psql -U postgres
CREATE DATABASE soap_notes_db;
\q
```

### 2. Set your environment variable

```bash
# Mac/Linux
export DATABASE_URL="postgresql://postgres:yourpassword@localhost:5432/soap_notes_db"

# Windows
set DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/soap_notes_db
```

### 3. Create all tables

**Option A — Using Python (recommended):**
```bash
cd database
python database.py
```

**Option B — Using raw SQL:**
```bash
psql -U postgres -d soap_notes_db -f schema.sql
```

---

##  How Shifaa (Backend) Uses This

In any FastAPI route, import `get_db` as a dependency:

```python
from database import get_db, Transcript
from sqlalchemy.orm import Session
from fastapi import Depends

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), db: Session = Depends(get_db)):
    record = Transcript(
        audio_filename=audio.filename,
        raw_transcript_text="..."
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"transcript": "...", "transcript_id": record.id}
```

##  Expected Project Structure

```
project/
├── main.py                  ← Shifaa's file (unchanged)
├── database/
│   ├── __init__.py
│   ├── database.py
│   ├── models.py
│   ├── schema.sql
│   └── README.md
└── app/
    ├── whisper_service.py
    └── gpt_service.py
```
