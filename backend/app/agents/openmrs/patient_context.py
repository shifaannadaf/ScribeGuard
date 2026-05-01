"""
OpenMRSPatientContextAgent — resolves the OpenMRS Patient resource for the
encounter AND fetches the relevant chart context (existing medications,
allergies, conditions, recent observations, encounters) so the physician
review UI can show the patient's existing record alongside the AI draft.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.config import settings


logger = logging.getLogger("scribeguard.agents.openmrs.patient_context")


class OpenMRSPatientContextAgent:
    name = "OpenMRSPatientContextAgent"
    version = "1.1.0"
    description = (
        "Resolves the OpenMRS Patient resource for an encounter and "
        "snapshots the existing chart (medications, allergies, conditions, "
        "observations, encounters)."
    )

    def resolve(
        self,
        *,
        openmrs_patient_uuid: Optional[str],
        local_patient_id: str,
    ) -> dict[str, Any]:
        if settings.OPENMRS_SIMULATE:
            uuid = openmrs_patient_uuid or f"sim-{local_patient_id}"
            return {
                "simulated":  True,
                "uuid":       uuid,
                "identifier": local_patient_id,
                "name":       "(simulated patient)",
                "raw":        {},
            }

        from app.openmrs.patient import get_patient_by_uuid, get_patient_by_identifier
        if openmrs_patient_uuid:
            patient = get_patient_by_uuid(openmrs_patient_uuid)
            uuid = patient.get("id") or openmrs_patient_uuid
        else:
            bundle = get_patient_by_identifier(local_patient_id)
            entries = bundle.get("entry") or []
            if not entries:
                raise RuntimeError(
                    f"No OpenMRS patient found with identifier '{local_patient_id}'."
                )
            patient = entries[0].get("resource") or {}
            uuid = patient.get("id")

        return {
            "simulated":  False,
            "uuid":       uuid,
            "identifier": local_patient_id,
            "name":       _flatten_name(patient.get("name") or []),
            "raw":        patient,
        }

    def fetch_chart_context(self, *, patient_uuid: str) -> dict[str, Any]:
        """Read existing chart entries for the patient. Errors per resource
        are captured but never abort the rest of the snapshot."""
        if settings.OPENMRS_SIMULATE:
            return {
                "existing_medications": [],
                "existing_allergies":   [],
                "existing_conditions":  [],
                "recent_observations":  [],
                "recent_encounters":    [],
                "errors": {},
            }

        from app.openmrs.patient import get_patient_by_uuid
        from app.openmrs.medication import get_medication_requests
        from app.openmrs.allergy import get_allergies
        from app.openmrs.condition import get_conditions
        from app.openmrs.observation import get_observations

        ctx: dict[str, Any] = {
            "existing_medications": [],
            "existing_allergies":   [],
            "existing_conditions":  [],
            "recent_observations":  [],
            "recent_encounters":    [],
            "errors": {},
        }

        try:
            ctx["existing_medications"] = _entries(get_medication_requests(patient_uuid))
        except Exception as exc:  # noqa: BLE001
            ctx["errors"]["medications"] = str(exc)
        try:
            ctx["existing_allergies"] = _entries(get_allergies(patient_uuid))
        except Exception as exc:  # noqa: BLE001
            ctx["errors"]["allergies"] = str(exc)
        try:
            ctx["existing_conditions"] = _entries(get_conditions(patient_uuid))
        except Exception as exc:  # noqa: BLE001
            ctx["errors"]["conditions"] = str(exc)
        try:
            ctx["recent_observations"] = _entries(get_observations(patient_uuid))[:25]
        except Exception as exc:  # noqa: BLE001
            ctx["errors"]["observations"] = str(exc)
        # Recent Encounter resources via direct REST call
        try:
            from app.openmrs.client import fhir_get
            ctx["recent_encounters"] = _entries(fhir_get("Encounter", params={"patient": patient_uuid}))[:10]
        except Exception as exc:  # noqa: BLE001
            ctx["errors"]["encounters"] = str(exc)
        # Demographics
        try:
            ctx["demographics"] = _flatten_demographics(get_patient_by_uuid(patient_uuid))
        except Exception as exc:  # noqa: BLE001
            ctx["errors"]["demographics"] = str(exc)
        return ctx


def _entries(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(bundle, dict):
        return []
    return [e.get("resource") or {} for e in (bundle.get("entry") or [])]


def _flatten_name(names: list[dict]) -> str:
    if not names:
        return ""
    n = names[0]
    given = " ".join(n.get("given") or [])
    family = n.get("family") or ""
    return f"{given} {family}".strip()


def _flatten_demographics(patient: dict) -> dict[str, Any]:
    return {
        "name":        _flatten_name(patient.get("name") or []),
        "gender":      patient.get("gender"),
        "birth_date":  patient.get("birthDate"),
        "active":      patient.get("active"),
        "identifiers": [
            {"system": i.get("system"), "value": i.get("value")}
            for i in (patient.get("identifier") or [])
        ],
    }
