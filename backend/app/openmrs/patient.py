"""
FHIR R4 Patient resource operations.

Endpoints used:
    GET  /Patient?identifier={id}   → search by OpenMRS ID (e.g. "10001YY")
    GET  /Patient/{uuid}            → fetch by UUID
"""

import logging
from .client import fhir_get

logger = logging.getLogger(__name__)


def get_patient_by_identifier(identifier: str) -> dict:
    """
    READ — Search for a patient by their OpenMRS identifier.

    GET /Patient?identifier={identifier}

    Returns a FHIR Bundle. Access the patient via:
        result["entry"][0]["resource"]

    Example:
        patient = get_patient_by_identifier("10001YY")
    """
    data = fhir_get("Patient", params={"identifier": identifier})
    logger.info("Patient search '%s' → %d result(s)", identifier, data.get("total", 0))
    return data


def get_patient_by_uuid(patient_uuid: str) -> dict:
    """
    READ — Fetch a single patient by their FHIR UUID.

    GET /Patient/{uuid}

    Returns the Patient resource directly (not a Bundle).

    Example:
        patient = get_patient_by_uuid("076154fc-381d-4805-a5b9-13b90f667717")
    """
    data = fhir_get(f"Patient/{patient_uuid}")
    logger.info("Fetched patient %s", patient_uuid)
    return data