"""
FHIR R4 AllergyIntolerance resource operations.

Endpoints used:
    GET    /AllergyIntolerance?patient={uuid}   → list allergies for a patient
    POST   /AllergyIntolerance                  → create a new allergy
    PATCH  /AllergyIntolerance/{uuid}           → partial update (JSON Patch)
    DELETE /AllergyIntolerance/{uuid}           → delete an allergy
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .client import fhir_get, fhir_post, fhir_patch, fhir_delete
from .config import DEFAULT_PRACTITIONER_UUID

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def get_allergies(patient_uuid: str) -> dict:
    """
    READ — List all allergies for a patient.

    GET /AllergyIntolerance?patient={uuid}

    Returns a FHIR Bundle of AllergyIntolerance resources.

    Example:
        allergies = get_allergies("076154fc-381d-4805-a5b9-13b90f667717")
    """
    data = fhir_get("AllergyIntolerance", params={"patient": patient_uuid})
    logger.info("Fetched %d allergy/allergies for patient %s",
                data.get("total", 0), patient_uuid)
    return data

def create_allergy(
    patient_uuid: str,
    substance_concept_uuid: str = "81725AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    substance_display: str = "Penicillin G",
    manifestation_concept_uuid: str = "121629AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    manifestation_display: str = "Anaemia",
    severity: str = "moderate",
    recorded_date: Optional[str] = None,
) -> dict:
    """
    CREATE — Record a new allergy for a patient.

    POST /AllergyIntolerance

    Args:
        patient_uuid:               Patient UUID
        substance_concept_uuid:     CIEL concept UUID for the allergen
        substance_display:          Human-readable allergen name
        manifestation_concept_uuid: CIEL concept UUID for the reaction
        manifestation_display:      Human-readable reaction name
        severity:                   "mild" | "moderate" | "severe"
        practitioner_uuid:          UUID of the recording clinician
        recorded_date:              ISO datetime string (defaults to now)

    Returns the created AllergyIntolerance resource with its UUID at ["id"].

    Example:
        allergy = create_allergy(
            patient_uuid="076154fc-...",
            substance_display="Penicillin",
            severity="severe",
        )
        allergy_uuid = allergy["id"]
    """
    recorded_date = recorded_date or _now_iso()

    payload = {
        "resourceType": "AllergyIntolerance",
        "clinicalStatus": {
            "coding": [{
                "system":  "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                "code":    "active",
                "display": "Active",
            }],
            "text": "Active",
        },
        "verificationStatus": {
            "coding": [{
                "system":  "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                "code":    "confirmed",
                "display": "Confirmed",
            }],
            "text": "Confirmed",
        },
        "type":        "allergy",
        "category":    ["medication"],
        "criticality": "unable-to-assess",
        "code": {
            "coding": [
                {"code": substance_concept_uuid, "display": substance_display},
                {"system": "https://cielterminology.org",
                 "code": substance_concept_uuid[:5]},
            ],
            "text": substance_display,
        },
        "patient":      {"reference": f"Patient/{patient_uuid}"},
        "recordedDate": recorded_date,
        "reaction": [{
            "substance": {
                "coding": [{"code": substance_concept_uuid, "display": substance_display}],
                "text":    substance_display,
            },
            "manifestation": [{
                "coding": [{"code": manifestation_concept_uuid,
                            "display": manifestation_display}],
                "text": manifestation_display,
            }],
            "severity": severity,
        }],
        "note": [{"text": ""}],
    }

    data = fhir_post("AllergyIntolerance", payload)
    logger.info("Created AllergyIntolerance UUID=%s for patient %s",
                data.get("id"), patient_uuid)
    return data


def update_allergy(allergy_uuid: str, json_patch: list[dict]) -> dict:
    """
    UPDATE — Partial update using JSON Patch (RFC 6902).

    PATCH /AllergyIntolerance/{uuid}
    Content-Type: application/json-patch+json

    Args:
        allergy_uuid: UUID of the AllergyIntolerance to update
        json_patch:   List of RFC 6902 patch operations

    Common patch examples:
        # Change severity
        [{"op": "replace", "path": "/reaction/0/severity", "value": "severe"}]

        # Mark as inactive
        [{"op": "replace", "path": "/clinicalStatus/coding/0/code", "value": "inactive"}]

    Example:
        updated = update_allergy(
            "eafc67d0-...",
            [{"op": "replace", "path": "/reaction/0/severity", "value": "severe"}]
        )
    """
    data = fhir_patch(f"AllergyIntolerance/{allergy_uuid}", json_patch)
    logger.info("Updated AllergyIntolerance %s", allergy_uuid)
    return data


def delete_allergy(allergy_uuid: str) -> bool:
    """
    DELETE — Remove an allergy record.

    DELETE /AllergyIntolerance/{uuid}

    Returns True on success.

    Example:
        delete_allergy("eafc67d0-0cf1-4fe3-a316-ed2a9c5dfa5c")
    """
    fhir_delete(f"AllergyIntolerance/{allergy_uuid}")
    logger.info("Deleted AllergyIntolerance %s", allergy_uuid)
    return True