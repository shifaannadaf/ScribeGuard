"""
Runs every CRUD operation against your OpenMRS Docker sandbox
using the exact UUIDs from the FHIR_LAB Postman collection.

Usage:
    cd backend
    pip install httpx python-dotenv
    python -m openmrs.verify

Expected output: checkmarks for every passing test, summary at the end.
"""

import sys
from .metadata    import get_metadata
from .patient     import get_patient_by_identifier, get_patient_by_uuid
from .encounter   import create_encounter
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
from .config import (
    DEFAULT_PATIENT_UUID, DEFAULT_PRACTITIONER_UUID,
    DEFAULT_SUPER_USER_UUID, DEFAULT_MEDICATION_UUID,
)

RESULTS: list[tuple[str, str]] = []


def check(label: str, fn, *args, **kwargs):
    """Run fn(*args, **kwargs), record PASS or FAIL."""
    try:
        result = fn(*args, **kwargs)
        RESULTS.append(("PASS", label))
        return result
    except Exception as e:
        RESULTS.append(("FAIL", f"{label}: {e}"))
        return None


def run():
    print("\n=== OpenMRS FHIR R4 — CRUD Verification ===\n")
    print(f"  Patient UUID : {DEFAULT_PATIENT_UUID}\n")

    # ── Metadata ──────────────────────────────────────────────────────────
    meta = check("GET /metadata", get_metadata)
    if meta:
        print(f"  FHIR version : {meta.get('fhirVersion', '?')}")

    # ── Patient ───────────────────────────────────────────────────────────
    check("GET patient by identifier (10001YY)", get_patient_by_identifier, "10001YY")
    check("GET patient by UUID",                 get_patient_by_uuid, DEFAULT_PATIENT_UUID)

    # ── Encounter ─────────────────────────────────────────────────────────
    # enc = check(
    #     "POST /Encounter",
    #     create_encounter,
    #     patient_ref=f"Patient/{DEFAULT_PATIENT_UUID}",
    #     practitioner_ref=f"Practitioner/{DEFAULT_PRACTITIONER_UUID}",
    # )
    # if enc:
    #     print(f"  Encounter UUID : {enc.get('id')}")

    # ── Allergy ───────────────────────────────────────────────────────────
    check("GET /AllergyIntolerance", get_allergies, DEFAULT_PATIENT_UUID)

    allergy = check(
        "POST /AllergyIntolerance  (Aspirin → Anaemia, moderate)",
        create_allergy,
        patient_uuid=DEFAULT_PATIENT_UUID,
    )
    if allergy:
        a_uuid = allergy["id"]
        print(f"  Allergy UUID : {a_uuid}")
        check(
            "PATCH /AllergyIntolerance  (severity → severe)",
            update_allergy, a_uuid,
            [{"op": "replace", "path": "/reaction/0/severity", "value": "severe"}],
        )
        check("DELETE /AllergyIntolerance", delete_allergy, a_uuid)

    # ── Condition ─────────────────────────────────────────────────────────
    check("GET /Condition", get_conditions, DEFAULT_PATIENT_UUID)

    cond = check(
        "POST /Condition  (Diabetes mellitus)",
        create_condition,
        patient_uuid=DEFAULT_PATIENT_UUID,
    )
    if cond:
        c_uuid = cond["id"]
        print(f"  Condition UUID : {c_uuid}")
        check(
            "PATCH /Condition  (status → inactive)",
            update_condition, c_uuid,
            [{"op": "replace", "path": "/clinicalStatus/coding/0/code", "value": "inactive"}],
        )
        check("DELETE /Condition", delete_condition, c_uuid)

    # ── Observations ──────────────────────────────────────────────────────
    check("GET /Observation (patient)", get_observations, DEFAULT_PATIENT_UUID)

    h  = check("POST /Observation height      (90.0 cm)",    create_obs_height,           DEFAULT_PATIENT_UUID, 90.0)
    w  = check("POST /Observation weight      (85.5 kg)",    create_obs_weight,           DEFAULT_PATIENT_UUID, 85.5)
    t  = check("POST /Observation temperature (36.8 °C)",    create_obs_temperature,      DEFAULT_PATIENT_UUID, 36.8)
    rr = check("POST /Observation resp rate   (18 bpm)",     create_obs_respiratory_rate, DEFAULT_PATIENT_UUID, 18.0)
    s  = check("POST /Observation SpO2        (98.0%)",      create_obs_spo2,             DEFAULT_PATIENT_UUID, 98.0)

    if h:
        check("GET  /Observation by UUID",         get_observation_by_uuid, h["id"])
        check("PUT  /Observation height (181 cm)", update_obs_height, h["id"], DEFAULT_PATIENT_UUID, 181.0)
    if w:
        check("PUT  /Observation weight (100 kg)", update_obs_weight, w["id"], DEFAULT_PATIENT_UUID, 100.0)

    for label, obs in [("height", h), ("weight", w), ("temperature", t), ("resp rate", rr), ("SpO2", s)]:
        if obs:
            check(f"DELETE /Observation ({label})", delete_observation, obs["id"])

    # ── Medication ────────────────────────────────────────────────────────
    check("GET /MedicationRequest",  get_medication_requests,  DEFAULT_PATIENT_UUID)
    check("GET /MedicationDispense", get_medication_dispenses, DEFAULT_PATIENT_UUID)

    dispense = check(
        "POST /MedicationDispense  (Paracetamol 500mg × 20)",
        create_medication_dispense,
        patient_uuid=DEFAULT_PATIENT_UUID,
        medication_uuid=DEFAULT_MEDICATION_UUID,
        performer_uuid=DEFAULT_SUPER_USER_UUID,
    )
    if dispense:
        print(f"  Dispense UUID : {dispense.get('id')}")

    # MedicationRequest PATCH — uncomment after running GET /medication-request
    # and pasting in a real UUID from your sandbox:
    #
    # MED_REQ_UUID = "paste-uuid-here"
    # check(
    #     "PATCH /MedicationRequest (status → stopped)",
    #     update_medication_request, MED_REQ_UUID,
    #     [{"op": "replace", "path": "/status", "value": "stopped"}],
    # )

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n=== Results ===\n")
    passes = [r for r in RESULTS if r[0] == "PASS"]
    fails  = [r for r in RESULTS if r[0] == "FAIL"]

    for status, label in RESULTS:
        icon = "✓" if status == "PASS" else "✗"
        print(f"  {icon}  {label}")

    print(f"\n  {len(passes)}/{len(RESULTS)} passed")

    if fails:
        print("\n  Failed:")
        for _, label in fails:
            print(f"    - {label}")
        sys.exit(1)
    else:
        print("\n  All checks passed — OpenMRS FHIR R4 sandbox is ready.\n")


if __name__ == "__main__":
    run()