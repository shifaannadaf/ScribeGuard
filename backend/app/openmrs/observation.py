"""
FHIR R4 Observation resource operations — vitals signs.

Endpoints used:
    GET    /Observation?patient={uuid}   → list all observations for a patient
    GET    /Observation/{uuid}           → get a single observation
    POST   /Observation                  → create a vital sign observation
    PUT    /Observation/{uuid}           → full update (replace) an observation
    DELETE /Observation/{uuid}           → delete an observation

Vitals covered (matching Postman collection):
    - Height       (CIEL 5090, cm)
    - Weight       (CIEL 5089, kg)
    - Temperature  (CIEL 5088, °C)
    - Resp. Rate   (CIEL 5242, breaths/min)
    - SpO2         (CIEL 5092, %)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .client import fhir_get, fhir_post, fhir_put, fhir_delete
from .config import CONCEPT

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


# ---------------------------------------------------------------------------
# Internal builder — keeps all 5 vital functions DRY
# ---------------------------------------------------------------------------

def _build_observation(
    patient_uuid: str,
    concept_key: str,
    display: str,
    ciel_code: str,
    value: float,
    unit: str,
    ucum_code: str,
    ref_low: float,
    ref_high: float,
    category_code: str = "vital-signs",
    category_display: str = "Vital Signs",
    obs_id: Optional[str] = None,
    effective_datetime: Optional[str] = None,
) -> dict:
    dt = effective_datetime or _now_iso()
    resource = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{
            "coding": [{
                "system":  "http://terminology.hl7.org/CodeSystem/observation-category",
                "code":    category_code,
                "display": category_display,
            }]
        }],
        "code": {
            "coding": [
                {"code": CONCEPT[concept_key], "display": display},
                {"system": "https://cielterminology.org", "code": ciel_code},
            ],
            "text": display,
        },
        "subject":         {"reference": f"Patient/{patient_uuid}"},
        "effectiveDateTime": dt,
        "issued":            dt,
        "valueQuantity": {
            "value":  value,
            "unit":   unit,
            "system": "http://unitsofmeasure.org",
            "code":   ucum_code,
        },
        "referenceRange": [{
            "low":  {"value": ref_low},
            "high": {"value": ref_high},
            "type": {"coding": [{
                "system": "http://fhir.openmrs.org/ext/obs/reference-range",
                "code":   "absolute",
            }]},
        }],
    }
    if obs_id:
        resource["id"] = obs_id   # required when doing a PUT
    return resource


# ===========================================================================
# READ
# ===========================================================================

def get_observations(patient_uuid: str) -> dict:
    """
    READ — List all observations for a patient.

    GET /Observation?patient={uuid}

    Returns a FHIR Bundle of Observation resources.

    Example:
        obs = get_observations("076154fc-381d-4805-a5b9-13b90f667717")
    """
    data = fhir_get("Observation", params={"patient": patient_uuid})
    logger.info("Fetched %d observation(s) for patient %s",
                data.get("total", 0), patient_uuid)
    return data


def get_observation_by_uuid(obs_uuid: str) -> dict:
    """
    READ — Fetch a single observation by UUID.

    GET /Observation/{uuid}

    Example:
        obs = get_observation_by_uuid("47087852-028c-4987-a6fe-ad9cd4ee93bd")
    """
    data = fhir_get(f"Observation/{obs_uuid}")
    logger.info("Fetched Observation %s", obs_uuid)
    return data


# ===========================================================================
# CREATE  (one function per vital type)
# ===========================================================================

def create_obs_height(
    patient_uuid: str,
    value_cm: float,
    effective_datetime: Optional[str] = None,
) -> dict:
    """
    CREATE — Record a height measurement.

    POST /Observation  (CIEL 5090, category: exam)

    Args:
        patient_uuid:        Patient UUID
        value_cm:            Height in centimetres (e.g. 90.0)
        effective_datetime:  ISO-8601 string (defaults to now)

    Example:
        obs = create_obs_height("076154fc-...", 175.0)
        obs_uuid = obs["id"]
    """
    payload = _build_observation(
        patient_uuid, "height", "Height (cm)", "5090",
        value_cm, "cm", "cm", 10.0, 272.0,
        category_code="exam", category_display="Exam",
        effective_datetime=effective_datetime,
    )
    data = fhir_post("Observation", payload)
    logger.info("Created height obs %.1f cm → UUID=%s", value_cm, data.get("id"))
    return data


def create_obs_weight(
    patient_uuid: str,
    value_kg: float,
    effective_datetime: Optional[str] = None,
) -> dict:
    """
    CREATE — Record a weight measurement.

    POST /Observation  (CIEL 5089, category: exam)

    Args:
        patient_uuid: Patient UUID
        value_kg:     Weight in kilograms (e.g. 85.5)

    Example:
        obs = create_obs_weight("076154fc-...", 85.5)
    """
    payload = _build_observation(
        patient_uuid, "weight", "Weight (kg)", "5089",
        value_kg, "kg", "kg", 0.0, 250.0,
        category_code="exam", category_display="Exam",
        effective_datetime=effective_datetime,
    )
    data = fhir_post("Observation", payload)
    logger.info("Created weight obs %.1f kg → UUID=%s", value_kg, data.get("id"))
    return data


def create_obs_temperature(
    patient_uuid: str,
    value_c: float,
    effective_datetime: Optional[str] = None,
) -> dict:
    """
    CREATE — Record a body temperature.

    POST /Observation  (CIEL 5088, category: vital-signs)

    Args:
        patient_uuid: Patient UUID
        value_c:      Temperature in Celsius (e.g. 36.8)

    Example:
        obs = create_obs_temperature("076154fc-...", 38.2)
    """
    payload = _build_observation(
        patient_uuid, "temperature", "Temperature (°C)", "5088",
        value_c, "°C", "Cel", 35.0, 42.0,
        effective_datetime=effective_datetime,
    )
    data = fhir_post("Observation", payload)
    logger.info("Created temperature obs %.1f °C → UUID=%s", value_c, data.get("id"))
    return data


def create_obs_respiratory_rate(
    patient_uuid: str,
    value_bpm: float,
    effective_datetime: Optional[str] = None,
) -> dict:
    """
    CREATE — Record a respiratory rate.

    POST /Observation  (CIEL 5242, category: vital-signs)

    Args:
        patient_uuid: Patient UUID
        value_bpm:    Breaths per minute (e.g. 18)

    Example:
        obs = create_obs_respiratory_rate("076154fc-...", 16.0)
    """
    payload = _build_observation(
        patient_uuid, "resp_rate", "Respiratory rate", "5242",
        value_bpm, "breaths/min", "/min", 12.0, 20.0,
        effective_datetime=effective_datetime,
    )
    data = fhir_post("Observation", payload)
    logger.info("Created resp rate obs %.0f bpm → UUID=%s", value_bpm, data.get("id"))
    return data


def create_obs_spo2(
    patient_uuid: str,
    value_pct: float,
    effective_datetime: Optional[str] = None,
) -> dict:
    """
    CREATE — Record an oxygen saturation (SpO2) reading.

    POST /Observation  (CIEL 5092, category: vital-signs)

    Args:
        patient_uuid: Patient UUID
        value_pct:    SpO2 percentage (e.g. 98.0)

    Example:
        obs = create_obs_spo2("076154fc-...", 98.0)
    """
    payload = _build_observation(
        patient_uuid, "spo2", "Oxygen saturation (SpO₂)", "5092",
        value_pct, "%", "%", 90.0, 100.0,
        effective_datetime=effective_datetime,
    )
    data = fhir_post("Observation", payload)
    logger.info("Created SpO2 obs %.1f%% → UUID=%s", value_pct, data.get("id"))
    return data


# ===========================================================================
# UPDATE  (PUT — full resource replacement, as in the collection)
# ===========================================================================

def update_obs_height(
    obs_uuid: str,
    patient_uuid: str,
    new_value_cm: float,
) -> dict:
    """
    UPDATE — Replace a height observation with a new value.

    PUT /Observation/{uuid}  (full resource replacement)

    Note: OpenMRS FHIR uses PUT (not PATCH) for Observation updates.
    The "id" field in the body must match the UUID in the URL.

    Example:
        updated = update_obs_height("272bb883-...", "076154fc-...", 181.0)
    """
    payload = _build_observation(
        patient_uuid, "height", "Height (cm)", "5090",
        new_value_cm, "cm", "cm", 10.0, 272.0,
        category_code="exam", category_display="Exam",
        obs_id=obs_uuid,
    )
    data = fhir_put(f"Observation/{obs_uuid}", payload)
    logger.info("Updated height obs %s → %.1f cm", obs_uuid, new_value_cm)
    return data


def update_obs_weight(
    obs_uuid: str,
    patient_uuid: str,
    new_value_kg: float,
) -> dict:
    """
    UPDATE — Replace a weight observation with a new value.

    PUT /Observation/{uuid}  (full resource replacement)

    Example:
        updated = update_obs_weight("7a519e7e-...", "076154fc-...", 100.0)
    """
    payload = _build_observation(
        patient_uuid, "weight", "Weight (kg)", "5089",
        new_value_kg, "kg", "kg", 0.0, 250.0,
        category_code="exam", category_display="Exam",
        obs_id=obs_uuid,
    )
    data = fhir_put(f"Observation/{obs_uuid}", payload)
    logger.info("Updated weight obs %s → %.1f kg", obs_uuid, new_value_kg)
    return data


# ===========================================================================
# DELETE
# ===========================================================================

def delete_observation(obs_uuid: str) -> bool:
    """
    DELETE — Remove an observation.

    DELETE /Observation/{uuid}

    Returns True on success.

    Example:
        delete_observation("71b6afba-50ee-44cf-adfb-98c28dd87e86")
    """
    fhir_delete(f"Observation/{obs_uuid}")
    logger.info("Deleted Observation %s", obs_uuid)
    return True