"""
FHIR R4 Immunization resource operations.

Endpoints used:
    GET    /Immunization?patient={uuid}   → list immunizations for a patient
    POST   /Immunization                  → create a new immunization record
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .client import fhir_get, fhir_post
from .config import DEFAULT_PRACTITIONER_UUID, DEFAULT_LOCATION_UUID

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def get_immunizations(patient_uuid: str) -> dict:
    """
    READ — List all immunizations for a patient.

    GET /Immunization?patient={uuid}

    Returns a FHIR Bundle of Immunization resources.
    """
    data = fhir_get("Immunization", params={"patient": patient_uuid})
    logger.info("Fetched %d immunization(s) for patient %s",
                data.get("total", 0), patient_uuid)
    return data


def create_immunization(
    patient_uuid: str,
    vaccine_name: str,
    encounter_uuid: Optional[str] = None,
    vaccine_code: str = "207",  # Generic vaccine code
    date_given: Optional[str] = None,
    lot_number: Optional[str] = None,
    site: Optional[str] = None,
    route: Optional[str] = None,
    practitioner_uuid: str = DEFAULT_PRACTITIONER_UUID,
    location_uuid: str = DEFAULT_LOCATION_UUID,
) -> dict:
    """
    CREATE — Record a new immunization for a patient.

    POST /Immunization

    Args:
        patient_uuid:       Patient UUID
        vaccine_name:       Human-readable vaccine name
        encounter_uuid:     Encounter UUID (optional but recommended)
        vaccine_code:       CVX vaccine code (default: "207" for generic)
        date_given:         ISO date string (defaults to today)
        lot_number:         Vaccine lot/batch number
        site:               Body site (e.g., "left deltoid")
        route:              Administration route (e.g., "IM")
        practitioner_uuid:  UUID of the administering clinician
        location_uuid:      UUID of the location

    Returns the created Immunization resource with its UUID at ["id"].

    Example:
        immunization = create_immunization(
            patient_uuid="076154fc-...",
            vaccine_name="COVID-19 mRNA Vaccine",
            lot_number="EN6201",
            site="left deltoid",
            route="IM"
        )
    """
    occurrence_datetime = date_given or _now_iso()

    payload = {
        "resourceType": "Immunization",
        "status": "completed",
        "vaccineCode": {
            "coding": [{
                "system": "http://hl7.org/fhir/sid/cvx",
                "code": vaccine_code,
                "display": vaccine_name
            }],
            "text": vaccine_name
        },
        "patient": {
            "reference": f"Patient/{patient_uuid}"
        },
        "occurrenceDateTime": occurrence_datetime,
        "recorded": _now_iso(),
        "performer": [{
            "actor": {
                "reference": f"Practitioner/{practitioner_uuid}"
            }
        }],
        "location": {
            "reference": f"Location/{location_uuid}"
        }
    }

    if encounter_uuid:
        payload["encounter"] = {
            "reference": f"Encounter/{encounter_uuid}"
        }

    if lot_number:
        payload["lotNumber"] = lot_number

    if site:
        payload["site"] = {
            "coding": [{
                "system": "http://snomed.info/sct",
                "display": site
            }],
            "text": site
        }

    if route:
        payload["route"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-RouteOfAdministration",
                "display": route
            }],
            "text": route
        }

    data = fhir_post("Immunization", payload)
    imm_uuid = data.get("id")
    logger.info("Created immunization %s for patient %s", imm_uuid, patient_uuid)
    return data
