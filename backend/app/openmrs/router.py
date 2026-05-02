"""
FastAPI router for all OpenMRS FHIR R4 endpoints.

Wire into your main FastAPI app with one line:

    from openmrs.router import router as openmrs_router
    app.include_router(openmrs_router)

Then visit http://localhost:8000/docs to test every endpoint interactively.

Prefix: /openmrs
Tags:   grouped by resource type in Swagger UI
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from .metadata    import get_metadata
from .patient     import search_patients, get_patient_by_identifier, get_patient_by_uuid
from .encounter   import get_encounters, create_encounter
from .allergy     import get_allergies, create_allergy, update_allergy, delete_allergy
from .condition   import get_conditions, create_condition, update_condition, delete_condition
from .observation import (
    get_observations, get_observation_by_uuid, delete_observation,
    create_obs_height, create_obs_weight, create_obs_temperature,
    create_obs_respiratory_rate, create_obs_spo2,
    update_obs_height, update_obs_weight,
)
from .medication  import (
    get_medication_requests, update_medication_request,
    get_medication_dispenses, create_medication_dispense,
)
from .config import DEFAULT_PRACTITIONER_UUID, DEFAULT_SUPER_USER_UUID, DEFAULT_MEDICATION_UUID

router = APIRouter(prefix="/openmrs", tags=["OpenMRS FHIR R4"])


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------

def _run(fn, *args, **kwargs):
    """Runs a service function and converts HTTP errors to FastAPI exceptions."""
    try:
        return fn(*args, **kwargs)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Request body schemas
# ---------------------------------------------------------------------------

class CreateEncounterBody(BaseModel):
    patient_ref: str                      # "Patient/076154fc-..."
    practitioner_ref: str                 # "Practitioner/82f18b44-..."
    location_ref: str = "Location/1"
    start: Optional[str] = None
    end:   Optional[str] = None

class CreateAllergyBody(BaseModel):
    patient_uuid: str
    substance_concept_uuid: str  = "71617AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    substance_display: str       = "Aspirin"
    manifestation_concept_uuid: str = "121629AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    manifestation_display: str   = "Anaemia"
    severity: str                = "moderate"
    practitioner_uuid: str       = DEFAULT_PRACTITIONER_UUID
    recorded_date: Optional[str] = None

class PatchBody(BaseModel):
    json_patch: list[dict]
    # RFC 6902 array, e.g.:
    # [{"op": "replace", "path": "/reaction/0/severity", "value": "severe"}]

class CreateConditionBody(BaseModel):
    patient_uuid: str
    icd10_code: str          = "E14.9"
    snomed_code: str         = "73211009"
    display: str             = "Diabetes mellitus"
    recorded_date: str       = "2025-10-02"
    onset_datetime: Optional[str] = None

class VitalBody(BaseModel):
    patient_uuid: str
    value: float
    effective_datetime: Optional[str] = None

class UpdateHeightBody(BaseModel):
    patient_uuid: str
    new_value_cm: float

class UpdateWeightBody(BaseModel):
    patient_uuid: str
    new_value_kg: float

class CreateDispenseBody(BaseModel):
    patient_uuid: str
    medication_uuid: str     = DEFAULT_MEDICATION_UUID
    medication_display: str  = "Paracetamol 500mg"
    quantity: float          = 20
    quantity_unit: str       = "Tablet"
    dose_value: float        = 1
    dose_unit: str           = "tablet"
    frequency: int           = 2
    performer_uuid: str      = DEFAULT_SUPER_USER_UUID
    when_handed_over: Optional[str] = None
    instructions: str        = "Take one tablet twice daily after meals"


# ===========================================================================
# METADATA
# ===========================================================================

@router.get("/metadata", summary="FHIR capability statement — server health check")
def route_metadata():
    return _run(get_metadata)


# ===========================================================================
# PATIENT
# ===========================================================================

@router.get("/patient", summary="Search patients by name or identifier")
def route_patient_search(q: str):
    return _run(search_patients, q)

@router.get("/patient/{patient_uuid}", summary="Get patient by UUID")
def route_patient_by_uuid(patient_uuid: str):
    return _run(get_patient_by_uuid, patient_uuid)


# ===========================================================================
# ENCOUNTER
# ===========================================================================

@router.get("/encounter", summary="Get encounters for a patient")
def route_encounter_get(patient_uuid: str):
    return _run(get_encounters, patient_uuid)

@router.post("/encounter", summary="Create encounter")
def route_encounter_create(body: CreateEncounterBody):
    return _run(create_encounter,
                body.patient_ref, body.practitioner_ref,
                body.location_ref, body.start, body.end)


# ===========================================================================
# ALLERGY
# ===========================================================================

@router.get("/allergy", summary="Get allergies for a patient")
def route_allergy_get(patient_uuid: str):
    return _run(get_allergies, patient_uuid)

@router.post("/allergy", summary="Create allergy")
def route_allergy_create(body: CreateAllergyBody):
    return _run(create_allergy,
                body.patient_uuid, body.substance_concept_uuid,
                body.substance_display, body.manifestation_concept_uuid,
                body.manifestation_display, body.severity,
                body.practitioner_uuid, body.recorded_date)

@router.patch("/allergy/{allergy_uuid}", summary="Update allergy (JSON Patch)")
def route_allergy_update(allergy_uuid: str, body: PatchBody):
    """
    Example body:
    ```json
    {"json_patch": [{"op": "replace", "path": "/reaction/0/severity", "value": "severe"}]}
    ```
    """
    return _run(update_allergy, allergy_uuid, body.json_patch)

@router.delete("/allergy/{allergy_uuid}", summary="Delete allergy")
def route_allergy_delete(allergy_uuid: str):
    _run(delete_allergy, allergy_uuid)
    return {"status": "deleted", "uuid": allergy_uuid}


# ===========================================================================
# CONDITION
# ===========================================================================

@router.get("/condition", summary="Get conditions for a patient")
def route_condition_get(patient_uuid: str):
    return _run(get_conditions, patient_uuid)

@router.post("/condition", summary="Create condition/diagnosis")
def route_condition_create(body: CreateConditionBody):
    return _run(create_condition,
                body.patient_uuid, body.icd10_code, body.snomed_code,
                body.display, body.recorded_date, body.onset_datetime)

@router.patch("/condition/{condition_uuid}", summary="Update condition (JSON Patch)")
def route_condition_update(condition_uuid: str, body: PatchBody):
    """
    Example body — mark inactive:
    ```json
    {"json_patch": [{"op": "replace", "path": "/clinicalStatus/coding/0/code", "value": "inactive"}]}
    ```
    """
    return _run(update_condition, condition_uuid, body.json_patch)

@router.delete("/condition/{condition_uuid}", summary="Delete condition")
def route_condition_delete(condition_uuid: str):
    _run(delete_condition, condition_uuid)
    return {"status": "deleted", "uuid": condition_uuid}


# ===========================================================================
# OBSERVATION
# ===========================================================================

@router.get("/observation", summary="Get all observations for a patient")
def route_obs_get(patient_uuid: str):
    return _run(get_observations, patient_uuid)

@router.get("/observation/{obs_uuid}", summary="Get single observation by UUID")
def route_obs_get_one(obs_uuid: str):
    return _run(get_observation_by_uuid, obs_uuid)

@router.post("/observation/height", summary="Create height observation (cm)")
def route_obs_height_create(body: VitalBody):
    return _run(create_obs_height, body.patient_uuid, body.value, body.effective_datetime)

@router.post("/observation/weight", summary="Create weight observation (kg)")
def route_obs_weight_create(body: VitalBody):
    return _run(create_obs_weight, body.patient_uuid, body.value, body.effective_datetime)

@router.post("/observation/temperature", summary="Create temperature observation (°C)")
def route_obs_temp_create(body: VitalBody):
    return _run(create_obs_temperature, body.patient_uuid, body.value, body.effective_datetime)

@router.post("/observation/respiratory-rate", summary="Create respiratory rate observation")
def route_obs_rr_create(body: VitalBody):
    return _run(create_obs_respiratory_rate, body.patient_uuid, body.value, body.effective_datetime)

@router.post("/observation/spo2", summary="Create SpO2 observation (%)")
def route_obs_spo2_create(body: VitalBody):
    return _run(create_obs_spo2, body.patient_uuid, body.value, body.effective_datetime)

@router.put("/observation/{obs_uuid}/height", summary="Update height observation (full PUT)")
def route_obs_height_update(obs_uuid: str, body: UpdateHeightBody):
    return _run(update_obs_height, obs_uuid, body.patient_uuid, body.new_value_cm)

@router.put("/observation/{obs_uuid}/weight", summary="Update weight observation (full PUT)")
def route_obs_weight_update(obs_uuid: str, body: UpdateWeightBody):
    return _run(update_obs_weight, obs_uuid, body.patient_uuid, body.new_value_kg)

@router.delete("/observation/{obs_uuid}", summary="Delete observation")
def route_obs_delete(obs_uuid: str):
    _run(delete_observation, obs_uuid)
    return {"status": "deleted", "uuid": obs_uuid}


# ===========================================================================
# MEDICATION
# ===========================================================================

@router.get("/medication-request", summary="Get medication requests for a patient")
def route_med_request_get(patient_uuid: str):
    return _run(get_medication_requests, patient_uuid)

@router.patch("/medication-request/{med_uuid}", summary="Update medication request (JSON Patch)")
def route_med_request_update(med_uuid: str, body: PatchBody):
    """
    Example body — stop a medication:
    ```json
    {"json_patch": [{"op": "replace", "path": "/status", "value": "stopped"}]}
    ```
    """
    return _run(update_medication_request, med_uuid, body.json_patch)

@router.get("/medication-dispense", summary="Get medication dispenses for a patient")
def route_med_dispense_get(patient_uuid: str):
    return _run(get_medication_dispenses, patient_uuid)

@router.post("/medication-dispense", summary="Create medication dispense")
def route_med_dispense_create(body: CreateDispenseBody):
    return _run(create_medication_dispense,
                body.patient_uuid, body.medication_uuid, body.medication_display,
                body.quantity, body.quantity_unit, body.dose_value, body.dose_unit,
                body.frequency, body.performer_uuid, body.when_handed_over,
                body.instructions)