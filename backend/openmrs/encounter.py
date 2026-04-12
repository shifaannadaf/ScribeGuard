"""
FHIR R4 Encounter resource operations.

Endpoints used:
    POST /Encounter    → create a new encounter (visit)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .client import fhir_post

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def create_encounter(
    patient_ref: str,
    practitioner_ref: str,
    location_ref: str = "Location/8d6c993e-c2cc-11de-8d13-0010c6dffd0f",
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> dict:
    """
    CREATE — Create a new ambulatory encounter.

    POST /Encounter

    Args:
        patient_ref:      FHIR reference, e.g. "Patient/076154fc-..."
        practitioner_ref: FHIR reference, e.g. "Practitioner/82f18b44-..."
        location_ref:     FHIR reference, defaults to "Location/1"
        start:            ISO-8601 datetime string (defaults to now)
        end:              ISO-8601 datetime string (defaults to now)

    Returns the created Encounter resource with its UUID at ["id"].

    Example:
        enc = create_encounter(
            patient_ref="Patient/076154fc-381d-4805-a5b9-13b90f667717",
            practitioner_ref="Practitioner/82f18b44-6814-11e8-923f-e9a88dcb533f",
        )
        encounter_uuid = enc["id"]
    """
    start = start or _now_iso()
    end   = end   or _now_iso()

    payload = {
        "resourceType": "Encounter",
        "status": "finished",
        "class": {
            "system":  "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code":    "AMB",
            "display": "ambulatory",
        },
        "subject":     {"reference": patient_ref},
        "period":      {"start": start, "end": end},
        "participant": [{"individual": {"reference": practitioner_ref}}],
        "location":    [{"location":   {"reference": location_ref}}],
    }

    data = fhir_post("Encounter", payload)
    logger.info("Created Encounter UUID=%s", data.get("id"))
    return data