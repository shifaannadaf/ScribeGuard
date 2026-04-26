"""
FHIR R4 Condition resource operations.

Endpoints used:
    GET    /Condition?patient={uuid}   → list conditions for a patient
    POST   /Condition                  → create a new condition/diagnosis
    PATCH  /Condition/{uuid}           → partial update (JSON Patch)
    DELETE /Condition/{uuid}           → delete a condition
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .client import fhir_get, fhir_post, fhir_patch, fhir_delete

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def get_conditions(patient_uuid: str) -> dict:
    """
    READ — List all conditions/diagnoses for a patient.

    GET /Condition?patient={uuid}

    Returns a FHIR Bundle of Condition resources.

    Example:
        conditions = get_conditions("076154fc-381d-4805-a5b9-13b90f667717")
    """
    data = fhir_get("Condition", params={"patient": patient_uuid})
    logger.info("Fetched %d condition(s) for patient %s",
                data.get("total", 0), patient_uuid)
    return data


def create_condition(
    patient_uuid: str,
    icd10_code: str = "E14.9",
    snomed_code: str = "73211009",
    display: str = "Diabetes mellitus",
    recorded_date: str = "2025-10-02",
    onset_datetime: Optional[str] = None,
) -> dict:
    """
    CREATE — Record a new condition/diagnosis for a patient.

    POST /Condition

    Uses dual coding: ICD-10-CM + SNOMED CT (as in the Postman collection).

    Args:
        patient_uuid:    Patient UUID
        icd10_code:      ICD-10-CM code (e.g. "E14.9")
        snomed_code:     SNOMED CT code  (e.g. "73211009")
        display:         Human-readable condition name
        recorded_date:   Date string "YYYY-MM-DD"
        onset_datetime:  ISO datetime string (defaults to now)

    Returns the created Condition resource with its UUID at ["id"].

    Example:
        cond = create_condition(
            patient_uuid="076154fc-...",
            icd10_code="J06.9",
            snomed_code="54150009",
            display="Upper respiratory infection",
        )
        condition_uuid = cond["id"]
    """
    onset_datetime = onset_datetime or _now_iso()

    payload = {
        "resourceType": "Condition",
        "clinicalStatus": {
            "coding": [{
                "system":  "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code":    "active",
                "display": "Active",
            }],
            "text": "Active",
        },
        "verificationStatus": {
            "coding": [{
                "system":  "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code":    "confirmed",
                "display": "Confirmed",
            }],
            "text": "Confirmed",
        },
        "category": [{
            "coding": [{
                "system":  "http://terminology.hl7.org/CodeSystem/condition-category",
                "code":    "problem-list-item",
                "display": "Problem List Item",
            }],
            "text": "Problem List Item",
        }],
        "code": {
            "coding": [
                {"system": "http://hl7.org/fhir/sid/icd-10-cm",
                 "code": icd10_code, "display": display},
                {"system": "http://snomed.info/sct",
                 "code": snomed_code,  "display": display},
            ],
            "text": display,
        },
        "subject":         {"reference": f"Patient/{patient_uuid}"},
        "recordedDate":    recorded_date,
        "onsetDateTime":   onset_datetime,
    }

    data = fhir_post("Condition", payload)
    logger.info("Created Condition UUID=%s for patient %s", data.get("id"), patient_uuid)
    return data


def update_condition(condition_uuid: str, json_patch: list[dict]) -> dict:
    """
    UPDATE — Partial update using JSON Patch (RFC 6902).

    PATCH /Condition/{uuid}
    Content-Type: application/json-patch+json

    Args:
        condition_uuid: UUID of the Condition to update
        json_patch:     List of RFC 6902 patch operations

    Common patch examples:
        # Mark condition as inactive (resolved)
        [{"op": "replace", "path": "/clinicalStatus/coding/0/code", "value": "inactive"}]

        # Mark as resolved
        [{"op": "replace", "path": "/clinicalStatus/coding/0/code", "value": "resolved"}]

    Example:
        updated = update_condition(
            "87f5a1f2-...",
            [{"op": "replace", "path": "/clinicalStatus/coding/0/code", "value": "inactive"}]
        )
    """
    data = fhir_patch(f"Condition/{condition_uuid}", json_patch)
    logger.info("Updated Condition %s", condition_uuid)
    return data


def delete_condition(condition_uuid: str) -> bool:
    """
    DELETE — Remove a condition record.

    DELETE /Condition/{uuid}

    Returns True on success.

    Example:
        delete_condition("87f5a1f2-1f73-4d67-9969-d096940606d3")
    """
    fhir_delete(f"Condition/{condition_uuid}")
    logger.info("Deleted Condition %s", condition_uuid)
    return True