"""
OpenMRSEncounterMapperAgent — maps a ScribeGuard SOAP note + extracted
clinical entities into the FHIR R4 resource shapes expected by OpenMRS.

The mapper is intentionally pure (no IO): given the source data it returns
the JSON payloads. The OpenMRSNoteWriterAgent does the actual POSTs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.config import settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


_VITAL_TO_CIEL = {
    "height":            ("5090AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "Height (cm)",            "cm",         "cm"),
    "weight":            ("5089AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "Weight (kg)",            "kg",         "kg"),
    "temperature":       ("5088AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "Temperature (°C)",       "°C",         "Cel"),
    "respiratory_rate":  ("5242AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "Respiratory rate",       "breaths/min","/min"),
    "spo2":              ("5092AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "Oxygen saturation",      "%",          "%"),
    "hr":                ("5087AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "Heart rate",             "bpm",        "/min"),
    "systolic_bp":       ("5085AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "Systolic blood pressure","mmHg",       "mm[Hg]"),
    "diastolic_bp":      ("5086AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "Diastolic blood pressure","mmHg",      "mm[Hg]"),
}


class OpenMRSEncounterMapperAgent:
    name = "OpenMRSEncounterMapperAgent"
    version = "1.1.0"
    description = (
        "Maps a finalized SOAP note and extracted clinical entities into "
        "FHIR R4 resources for OpenMRS write-back."
    )

    # ── Encounter + clinical-note Observation ───────────────────────────

    def build_encounter_payload(
        self,
        *,
        patient_uuid: str,
        practitioner_uuid: str,
        location_uuid: str,
        when: str | None = None,
    ) -> dict[str, Any]:
        ts = when or _now_iso()
        return {
            "resourceType": "Encounter",
            "status": "finished",
            "class": {
                "system":  "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code":    "AMB",
                "display": "ambulatory",
            },
            "subject":     {"reference": f"Patient/{patient_uuid}"},
            "period":      {"start": ts, "end": ts},
            "participant": [{"individual": {"reference": f"Practitioner/{practitioner_uuid}"}}],
            "location":    [{"location":   {"reference": f"Location/{location_uuid}"}}],
        }

    def build_clinical_note_observation(
        self,
        *,
        patient_uuid: str,
        encounter_uuid: str,
        soap_markdown: str,
        when: str | None = None,
    ) -> dict[str, Any]:
        ts = when or _now_iso()
        return {
            "resourceType": "Observation",
            "status": "final",
            "category": [{
                "coding": [{
                    "system":  "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code":    "exam",
                    "display": "Exam",
                }],
            }],
            "code": {
                "coding": [{
                    "system":  "http://loinc.org",
                    "code":    "11506-3",
                    "display": "Progress note",
                }],
                "text": "ScribeGuard SOAP Note",
            },
            "subject":         {"reference": f"Patient/{patient_uuid}"},
            "encounter":       {"reference": f"Encounter/{encounter_uuid}"},
            "effectiveDateTime": ts,
            "issued":           ts,
            "valueString":      soap_markdown,
        }

    def soap_to_markdown(
        self,
        *,
        patient_name: str,
        patient_id: str,
        subjective: str,
        objective: str,
        assessment: str,
        plan: str,
    ) -> str:
        max_chars = 30_000
        body = (
            f"# ScribeGuard Clinical Note\n\n"
            f"- Patient: {patient_name} ({patient_id})\n"
            f"- Generated: {_now_iso()}\n\n"
            f"## Subjective\n{subjective}\n\n"
            f"## Objective\n{objective}\n\n"
            f"## Assessment\n{assessment}\n\n"
            f"## Plan\n{plan}\n"
        )
        if len(body) > max_chars:
            body = body[: max_chars - 100] + "\n\n... (truncated)"
        return body

    # ── Vital signs ──────────────────────────────────────────────────────

    def build_vital_observation(
        self,
        *,
        patient_uuid: str,
        encounter_uuid: str,
        kind: str,
        value: float,
        unit: Optional[str] = None,
        when: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        meta = _VITAL_TO_CIEL.get(kind)
        if not meta:
            return None
        ciel_uuid, display, default_unit, ucum = meta
        ts = when or _now_iso()
        return {
            "resourceType": "Observation",
            "status": "final",
            "category": [{
                "coding": [{
                    "system":  "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code":    "vital-signs",
                    "display": "Vital Signs",
                }],
            }],
            "code": {
                "coding": [{"code": ciel_uuid, "display": display}],
                "text": display,
            },
            "subject":           {"reference": f"Patient/{patient_uuid}"},
            "encounter":         {"reference": f"Encounter/{encounter_uuid}"},
            "effectiveDateTime": ts,
            "issued":            ts,
            "valueQuantity": {
                "value":  value,
                "unit":   unit or default_unit,
                "system": "http://unitsofmeasure.org",
                "code":   ucum,
            },
        }

    # ── Allergies ────────────────────────────────────────────────────────

    def build_allergy(
        self,
        *,
        patient_uuid: str,
        substance: str,
        reaction: Optional[str],
        severity: Optional[str],
        category: Optional[str],
        recorded_date: Optional[str] = None,
    ) -> dict[str, Any]:
        ts = recorded_date or _now_iso()
        sev = (severity or "").lower()
        if sev not in ("mild", "moderate", "severe"):
            sev = "moderate"
        cat = (category or "medication").lower()
        if cat not in ("medication", "food", "environment", "biologic"):
            cat = "medication"
        return {
            "resourceType": "AllergyIntolerance",
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}],
                "text": "Active",
            },
            "verificationStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}],
                "text": "Confirmed",
            },
            "type":     "allergy",
            "category": [cat],
            "criticality": "high" if sev == "severe" else "low",
            "code":     {"text": substance},
            "patient":  {"reference": f"Patient/{patient_uuid}"},
            "recordedDate": ts,
            "reaction": [{
                "manifestation": [{"text": reaction or "Reaction not specified"}],
                "severity": sev,
            }],
        }

    # ── Conditions ───────────────────────────────────────────────────────

    def build_condition(
        self,
        *,
        patient_uuid: str,
        description: str,
        icd10_code: Optional[str],
        snomed_code: Optional[str],
        clinical_status: Optional[str] = "active",
        verification: Optional[str] = "provisional",
        recorded_date: Optional[str] = None,
        onset_datetime: Optional[str] = None,
    ) -> dict[str, Any]:
        ts = recorded_date or _now_iso()
        codings: list[dict[str, str]] = []
        if icd10_code:
            codings.append({"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": icd10_code, "display": description})
        if snomed_code:
            codings.append({"system": "http://snomed.info/sct", "code": snomed_code, "display": description})
        if not codings:
            codings.append({"display": description})
        return {
            "resourceType": "Condition",
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": (clinical_status or "active")}],
                "text": (clinical_status or "active").title(),
            },
            "verificationStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": (verification or "provisional")}],
                "text": (verification or "provisional").title(),
            },
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                    "code": "encounter-diagnosis",
                    "display": "Encounter Diagnosis",
                }],
            }],
            "code": {"coding": codings, "text": description},
            "subject": {"reference": f"Patient/{patient_uuid}"},
            "recordedDate": ts,
            "onsetDateTime": onset_datetime or ts,
        }

    # ── Medication request ──────────────────────────────────────────────

    def build_medication_request(
        self,
        *,
        patient_uuid: str,
        encounter_uuid: str,
        practitioner_uuid: str,
        name: str,
        dose: Optional[str],
        route: Optional[str],
        frequency: Optional[str],
        duration: Optional[str],
        indication: Optional[str],
    ) -> dict[str, Any]:
        instructions_parts = [p for p in [dose, frequency, route, duration] if p]
        instruction_text = ", ".join(instructions_parts) or name
        return {
            "resourceType": "MedicationRequest",
            "status": "active",
            "intent": "order",
            "subject":   {"reference": f"Patient/{patient_uuid}"},
            "encounter": {"reference": f"Encounter/{encounter_uuid}"},
            "requester": {"reference": f"Practitioner/{practitioner_uuid}"},
            "medicationCodeableConcept": {"text": name},
            "authoredOn": _now_iso(),
            "reasonCode": [{"text": indication}] if indication else [],
            "dosageInstruction": [{
                "text": instruction_text,
                "route": {"text": route} if route else None,
                "timing": {"code": {"text": frequency}} if frequency else None,
            }],
            "note": [{"text": f"ScribeGuard: {instruction_text}"}],
        }

    def default_practitioner_uuid(self) -> str:
        return settings.OPENMRS_DEFAULT_PRACTITIONER_UUID

    def default_location_uuid(self) -> str:
        return settings.OPENMRS_DEFAULT_LOCATION_UUID
