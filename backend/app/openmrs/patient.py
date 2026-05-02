"""
FHIR R4 Patient resource operations.

Endpoints used:
    GET  /Patient?name={query}      → search by name (partial match)
    GET  /Patient?identifier={id}   → search by OpenMRS ID (e.g. "10001YY")
    GET  /Patient/{uuid}            → fetch by UUID
    POST /Patient                   → create a new patient
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from .client import fhir_get, fhir_post

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def search_patients(query: str) -> dict:
    """
    SEARCH — Find patients by name or identifier in a single call.

    Tries name search first; if zero results, falls back to identifier search.

    GET /Patient?name={query}
    GET /Patient?identifier={query}  (fallback)
    """
    data = fhir_get("Patient", params={"name": query})
    if data.get("total", 0) == 0:
        data = fhir_get("Patient", params={"identifier": query})
    logger.info("Patient search '%s' → %d result(s)", query, data.get("total", 0))
    return data


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


def create_patient(
    given_name: str,
    family_name: str,
    identifier: str,
    gender: str = "unknown",
    birthdate: Optional[str] = None,
) -> dict:
    """
    CREATE — Register a new patient in OpenMRS.

    POST /Patient

    Args:
        given_name:  Patient's first/given name
        family_name: Patient's last/family name
        identifier:  Patient identifier (e.g., "P-00123")
        gender:      "male" | "female" | "other" | "unknown"
        birthdate:   ISO date string (YYYY-MM-DD), optional

    Returns the created Patient resource with its UUID at ["id"].

    Example:
        patient = create_patient(
            given_name="John",
            family_name="Doe",
            identifier="P-00123",
            gender="male",
            birthdate="1985-06-12"
        )
        patient_uuid = patient["id"]
    """
    # Split full name if it's provided as a single string
    if " " in given_name and not family_name:
        parts = given_name.split(" ", 1)
        given_name = parts[0]
        family_name = parts[1] if len(parts) > 1 else ""

    payload = {
        "resourceType": "Patient",
        "active": True,
        "name": [{
            "use": "official",
            "family": family_name,
            "given": [given_name]
        }],
        "gender": gender.lower(),
        "identifier": [{
            "use": "official",
            "system": "http://hospital.smarthealthit.org",
            "value": identifier
        }]
    }

    if birthdate:
        payload["birthDate"] = birthdate

    data = fhir_post("Patient", payload)
    patient_uuid = data.get("id")
    logger.info("Created patient %s %s (UUID: %s, ID: %s)", 
                given_name, family_name, patient_uuid, identifier)
    return data