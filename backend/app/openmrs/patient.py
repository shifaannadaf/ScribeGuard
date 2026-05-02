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


def search_patients(query: str, max_results: int = 10) -> list[dict]:
    """
    Search patients by name OR identifier.

    Tries identifier first (exact OpenMRS ID like "10001YY"), then falls
    back to name search. Returns a flat list:
        [{"uuid", "name", "identifier", "gender", "birthDate"}, ...]
    """
    def _parse_bundle(bundle: dict) -> list[dict]:
        patients = []
        for entry in bundle.get("entry") or []:
            res = entry.get("resource", {})
            if res.get("resourceType") != "Patient":
                continue
            name_obj = (res.get("name") or [{}])[0]
            given = " ".join(name_obj.get("given") or [])
            family = name_obj.get("family", "")
            identifier = ""
            for ident in res.get("identifier") or []:
                val = ident.get("value", "")
                if val:
                    identifier = val
                    break
            patients.append({
                "uuid":       res.get("id", ""),
                "name":       f"{given} {family}".strip(),
                "identifier": identifier,
                "gender":     res.get("gender", ""),
                "birthDate":  res.get("birthDate", ""),
            })
        return patients

    # Try exact identifier first, fall back to name search
    results: list[dict] = []
    try:
        bundle = fhir_get("Patient", params={"identifier": query, "_count": max_results})
        results = _parse_bundle(bundle)
    except Exception:
        pass

    if not results:
        try:
            bundle = fhir_get("Patient", params={"name": query, "_count": max_results})
            results = _parse_bundle(bundle)
        except Exception:
            pass

    logger.info("Patient search '%s' → %d result(s)", query, len(results))
    return results


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