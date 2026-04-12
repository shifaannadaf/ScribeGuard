# OpenMRS FHIR R4 Module

FHIR R4 integration layer for the ScribeGuard medical transcription system. Handles all read/write/update/delete operations against an OpenMRS instance using the FHIR R4 API.

---

## Folder Structure

```
backend/openmrs/
├── __init__.py        # Package exports
├── config.py          # Environment config and shared UUIDs
├── client.py          # Shared HTTP client (auth, headers)
├── metadata.py        # GET /metadata — server health check
├── patient.py         # Patient read operations
├── encounter.py       # Encounter create
├── allergy.py         # AllergyIntolerance CRUD
├── condition.py       # Condition CRUD
├── observation.py     # Observation CRUD (all 5 vitals)
├── medication.py      # MedicationRequest + MedicationDispense
├── router.py          # FastAPI router — all endpoints
└── verify.py          # End-to-end verification script
```

---

## Setup

### 1. Environment Variables

Create a `.env` file in the `backend/` root:

```env
FHIR_SERVER=http://localhost/openmrs/ws/fhir2/R4
OPENMRS_USER=Admin
OPENMRS_PASSWORD=Admin123
```

### 2. Install Dependencies

```bash
pip install httpx python-dotenv fastapi uvicorn
```

Or with the requirements file:

```bash
pip install -r requirements.txt
```

### 3. Start OpenMRS (Docker)

```bash
docker start openmrs-backend-1 openmrs-frontend-1 openmrs-gateway-1
```

Wait for OpenMRS to be available at `http://localhost/openmrs`.

---

## Wire into FastAPI

In `backend/main.py`:

```python
from openmrs.router import router as openmrs_router

app.include_router(openmrs_router)
```

All endpoints will appear under `/openmrs/` in Swagger at `http://localhost:8000/docs`.

---

## API Endpoints

### Metadata
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/openmrs/metadata` | FHIR capability statement / server health |

### Patient
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/openmrs/patient?identifier=10001YY` | Search by OpenMRS identifier |
| GET | `/openmrs/patient/{uuid}` | Fetch patient by UUID |

### Encounter
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/openmrs/encounter` | Create a new encounter |

### Allergy Intolerance
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/openmrs/allergy?patient_uuid={uuid}` | List allergies for a patient |
| POST | `/openmrs/allergy` | Record a new allergy |
| PATCH | `/openmrs/allergy/{uuid}` | Update allergy (JSON Patch) |
| DELETE | `/openmrs/allergy/{uuid}` | Delete an allergy |

### Condition
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/openmrs/condition?patient_uuid={uuid}` | List conditions for a patient |
| POST | `/openmrs/condition` | Record a new condition/diagnosis |
| PATCH | `/openmrs/condition/{uuid}` | Update condition (JSON Patch) |
| DELETE | `/openmrs/condition/{uuid}` | Delete a condition |

### Observation (Vitals)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/openmrs/observation?patient_uuid={uuid}` | List all observations |
| GET | `/openmrs/observation/{uuid}` | Get single observation |
| POST | `/openmrs/observation/height` | Record height (cm) |
| POST | `/openmrs/observation/weight` | Record weight (kg) |
| POST | `/openmrs/observation/temperature` | Record temperature (°C) |
| POST | `/openmrs/observation/respiratory-rate` | Record respiratory rate |
| POST | `/openmrs/observation/spo2` | Record SpO2 (%) |
| PUT | `/openmrs/observation/{uuid}/height` | Update height |
| PUT | `/openmrs/observation/{uuid}/weight` | Update weight |
| DELETE | `/openmrs/observation/{uuid}` | Delete an observation |

### Medication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/openmrs/medication-request?patient_uuid={uuid}` | List medication requests |
| PATCH | `/openmrs/medication-request/{uuid}` | Update medication request (JSON Patch) |
| GET | `/openmrs/medication-dispense?patient_uuid={uuid}` | List medication dispenses |
| POST | `/openmrs/medication-dispense` | Record a medication dispense |

---

## Update Pattern (JSON Patch)

Updates use [RFC 6902 JSON Patch](https://datatracker.ietf.org/doc/html/rfc6902) with `Content-Type: application/json-patch+json`.

**Example — mark allergy severity as severe:**
```json
{
  "json_patch": [
    { "op": "replace", "path": "/reaction/0/severity", "value": "severe" }
  ]
}
```

**Example — mark condition as inactive:**
```json
{
  "json_patch": [
    { "op": "replace", "path": "/clinicalStatus/coding/0/code", "value": "inactive" }
  ]
}
```

**Example — stop a medication:**
```json
{
  "json_patch": [
    { "op": "replace", "path": "/status", "value": "stopped" }
  ]
}
```

---

## Verification

Run the full end-to-end test suite against your live OpenMRS instance:

```bash
cd backend
python3 -m openmrs.verify
```

Expected output when everything is working:

```
=== OpenMRS FHIR R4 — CRUD Verification ===

  FHIR version : 4.0.1

=== Results ===

  ✓  GET /metadata
  ✓  GET patient by identifier
  ✓  GET patient by UUID
  ✓  GET /AllergyIntolerance
  ✓  POST /AllergyIntolerance
  ✓  PATCH /AllergyIntolerance
  ✓  DELETE /AllergyIntolerance
  ✓  GET /Condition
  ✓  POST /Condition
  ✓  PATCH /Condition
  ✓  DELETE /Condition
  ✓  GET /Observation
  ✓  POST /Observation height
  ✓  POST /Observation weight
  ✓  POST /Observation temperature
  ✓  POST /Observation resp rate
  ✓  POST /Observation SpO2
  ✓  GET /Observation by UUID
  ✓  PUT /Observation height
  ✓  PUT /Observation weight
  ✓  DELETE /Observation x5
  ✓  GET /MedicationRequest
  ✓  GET /MedicationDispense
  ✓  POST /MedicationDispense

  28/28 passed — OpenMRS FHIR R4 sandbox is ready.
```

---

## FHIR Resources Covered

| Resource | GET | POST | PATCH | PUT | DELETE |
|----------|-----|------|-------|-----|--------|
| Patient | ✅ | — | — | — | — |
| Encounter | — | ✅ | — | — | — |
| AllergyIntolerance | ✅ | ✅ | ✅ | — | ✅ |
| Condition | ✅ | ✅ | ✅ | — | ✅ |
| Observation | ✅ | ✅ | — | ✅ | ✅ |
| MedicationRequest | ✅ | — | ✅ | — | — |
| MedicationDispense | ✅ | ✅ | — | — | — |

---

## CIEL Concept Codes Used

| Vital | CIEL Code |
|-------|-----------|
| Height (cm) | `5090` |
| Weight (kg) | `5089` |
| Temperature (°C) | `5088` |
| Respiratory Rate | `5242` |
| SpO2 (%) | `5092` |

---

## Sprint Context

| Sprint | Status |
|--------|--------|
| Sprint 1 — OpenMRS sandbox setup + FHIR CRUD | ✅ Complete |
| Sprint 2 — SOAP note write-back via `/openmrs/soap-note` | 🔜 Upcoming |
| Sprint 3 — End-to-end testing + architecture diagram | 🔜 Upcoming |

The `write_soap_note_to_fhir()` helper in `openmrs_fhir_service.py` is pre-built for Sprint 2 — it creates an Encounter + Condition + Observations from an approved SOAP note in one call.