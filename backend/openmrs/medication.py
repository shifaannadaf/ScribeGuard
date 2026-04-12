"""
FHIR R4 Medication resource operations.

Endpoints used:
    GET    /MedicationRequest?patient={uuid}    → list medication requests
    PATCH  /MedicationRequest/{uuid}            → update request (JSON Patch)
    GET    /MedicationDispense?patient={uuid}   → list medication dispenses
    POST   /MedicationDispense                  → record a new dispense
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .client import fhir_get, fhir_post, fhir_patch
from .config import DEFAULT_MEDICATION_UUID, DEFAULT_SUPER_USER_UUID

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


# ===========================================================================
# MEDICATION REQUEST
# ===========================================================================

def get_medication_requests(patient_uuid: str) -> dict:
    """
    READ — List all medication requests (prescriptions) for a patient.

    GET /MedicationRequest?patient={uuid}

    Returns a FHIR Bundle of MedicationRequest resources.

    Example:
        requests = get_medication_requests("076154fc-381d-4805-a5b9-13b90f667717")
        # To get the UUID of the first request:
        med_uuid = requests["entry"][0]["resource"]["id"]
    """
    data = fhir_get("MedicationRequest", params={"patient": patient_uuid})
    logger.info("Fetched %d medication request(s) for patient %s",
                data.get("total", 0), patient_uuid)
    return data


def update_medication_request(
    med_request_uuid: str,
    json_patch: list[dict],
) -> dict:
    """
    UPDATE — Partial update on a MedicationRequest using JSON Patch.

    PATCH /MedicationRequest/{uuid}
    Content-Type: application/json-patch+json

    Args:
        med_request_uuid: UUID of the MedicationRequest to update
        json_patch:       List of RFC 6902 patch operations

    Common patch examples:
        # Stop/discontinue a medication
        [{"op": "replace", "path": "/status", "value": "stopped"}]

        # Put on hold
        [{"op": "replace", "path": "/status", "value": "on-hold"}]

        # Reactivate
        [{"op": "replace", "path": "/status", "value": "active"}]

    Example:
        updated = update_medication_request(
            "d7c6d3db-6283-492a-be3c-48ca93b64488",
            [{"op": "replace", "path": "/status", "value": "stopped"}]
        )
    """
    data = fhir_patch(f"MedicationRequest/{med_request_uuid}", json_patch)
    logger.info("Updated MedicationRequest %s", med_request_uuid)
    return data


# ===========================================================================
# MEDICATION DISPENSE
# ===========================================================================

def get_medication_dispenses(patient_uuid: str) -> dict:
    """
    READ — List all medication dispenses for a patient.

    GET /MedicationDispense?patient={uuid}

    Returns a FHIR Bundle of MedicationDispense resources.

    Example:
        dispenses = get_medication_dispenses("076154fc-381d-4805-a5b9-13b90f667717")
    """
    data = fhir_get("MedicationDispense", params={"patient": patient_uuid})
    logger.info("Fetched %d dispense(s) for patient %s",
                data.get("total", 0), patient_uuid)
    return data


def create_medication_dispense(
    patient_uuid: str,
    medication_uuid: str = DEFAULT_MEDICATION_UUID,
    medication_display: str = "Paracetamol 500mg",
    quantity: float = 20,
    quantity_unit: str = "Tablet",
    dose_value: float = 1,
    dose_unit: str = "tablet",
    frequency: int = 2,
    performer_uuid: str = DEFAULT_SUPER_USER_UUID,
    when_handed_over: Optional[str] = None,
    instructions: str = "Take one tablet twice daily after meals",
) -> dict:
    """
    CREATE — Record a medication dispense event.

    POST /MedicationDispense

    Args:
        patient_uuid:      Patient UUID
        medication_uuid:   UUID of the Medication resource (Paracetamol 500mg default)
        medication_display: Human-readable medication name
        quantity:          Number of units dispensed (e.g. 20)
        quantity_unit:     Unit name (e.g. "Tablet")
        dose_value:        Dose per administration (e.g. 1)
        dose_unit:         Dose unit (e.g. "tablet")
        frequency:         Times per period (e.g. 2 = twice daily)
        performer_uuid:    UUID of the dispensing practitioner
        when_handed_over:  ISO datetime string (defaults to now)
        instructions:      Free-text dosage instructions

    Returns the created MedicationDispense resource with its UUID at ["id"].

    Example:
        dispense = create_medication_dispense(
            patient_uuid="076154fc-...",
            medication_display="Ibuprofen 400mg",
            quantity=30,
            instructions="Take one tablet three times daily with food",
        )
        dispense_uuid = dispense["id"]
    """
    when_handed_over = when_handed_over or _now_iso()

    payload = {
        "resourceType": "MedicationDispense",
        "status":  "completed",
        "subject": {"reference": f"Patient/{patient_uuid}"},
        "medicationReference": {
            "reference": f"Medication/{medication_uuid}",
            "display":   medication_display,
        },
        "quantity": {
            "value": quantity,
            "unit":  quantity_unit,
        },
        "whenHandedOver": when_handed_over,
        "dosageInstruction": [{
            "text": instructions,
            "timing": {
                "repeat": {
                    "frequency":  frequency,
                    "period":     1,
                    "periodUnit": "d",
                }
            },
            "route": {
                "coding": [{
                    "system":  "http://snomed.info/sct",
                    "code":    "26643006",
                    "display": "Oral",
                }]
            },
            "doseAndRate": [{
                "doseQuantity": {
                    "value": dose_value,
                    "unit":  dose_unit,
                }
            }],
        }],
        "performer": [{
            "actor": {"reference": f"Practitioner/{performer_uuid}"}
        }],
    }

    data = fhir_post("MedicationDispense", payload)
    logger.info("Created MedicationDispense UUID=%s for patient %s",
                data.get("id"), patient_uuid)
    return data