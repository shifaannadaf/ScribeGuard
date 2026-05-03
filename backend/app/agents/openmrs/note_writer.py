"""
OpenMRSNoteWriterAgent — writes all clinical entities to OpenMRS.

Uses the OpenMRS REST API (/ws/rest/v1/) for all entity types, with
dynamic concept/drug UUID lookup by name (following the EHR_script.py
pattern). FHIR is kept only for the clinical-note Observation (SOAP text).

Entity write strategy:
    Encounter        → REST  POST /ws/rest/v1/encounter
    SOAP Observation → REST  POST /ws/rest/v1/obs  (Text of encounter note)
    SOAP PDF         → REST  POST /ws/rest/v1/attachment  (multipart/form-data)
    Vital signs      → REST  POST /ws/rest/v1/obs  (concept lookup by name)
    Allergies        → REST  POST /ws/rest/v1/patient/{uuid}/allergy
    Conditions       → REST  POST /ws/rest/v1/condition
    Medications      → REST  POST /ws/rest/v1/order  (type=drugorder)
"""
from __future__ import annotations

import logging
import uuid as _uuid
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger("scribeguard.agents.openmrs.note_writer")

# ── REST base URL (derived from FHIR_SERVER) ──────────────────────────────
# FHIR_SERVER = "http://localhost:8080/openmrs/ws/fhir2/R4"
# REST_BASE   = "http://localhost:8080/openmrs"
_REST_BASE: str = settings.FHIR_SERVER.split("/ws/fhir2")[0].rstrip("/")

# Vital sign kind → OpenMRS concept name (used for REST obs lookup)
_VITAL_CONCEPT_NAME: dict[str, str] = {
    "height":           "Height (cm)",
    "weight":           "Weight (kg)",
    "temperature":      "Temperature (C)",
    "respiratory_rate": "Respiratory rate",
    "spo2":             "Oxygen saturation",
    "hr":               "Pulse",
    "systolic_bp":      "Systolic blood pressure",
    "diastolic_bp":     "Diastolic blood pressure",
    "blood_glucose":    "Blood glucose",
}

# Dose unit abbreviation → full OpenMRS concept name
_DOSE_UNIT_ALIAS: dict[str, str] = {
    "mg":    "milligram",
    "mcg":   "microgram",
    "g":     "gram",
    "ml":    "milliliter",
    "mL":    "milliliter",
    "l":     "liter",
    "L":     "liter",
    "unit":  "International Unit",
    "units": "International Unit",
    "iu":    "International Unit",
    "meq":   "milliequivalent",
}

# Allergy category → OpenMRS allergenType enum
_ALLERGY_TYPE: dict[str, str] = {
    "food":        "FOOD",
    "medication":  "DRUG",
    "drug":        "DRUG",
    "environment": "ENVIRONMENT",
    "biologic":    "DRUG",
}

# Severity display → OpenMRS concept name
_SEVERITY_CONCEPT: dict[str, str] = {
    "mild":     "Mild",
    "moderate": "Moderate",
    "severe":   "Severe",
}


def _auth_header() -> str:
    import base64
    token = base64.b64encode(
        f"{settings.OPENMRS_USER}:{settings.OPENMRS_PASSWORD}".encode()
    ).decode()
    return f"Basic {token}"


def _rest_get(path: str, params: Optional[dict] = None) -> dict:
    url = f"{_REST_BASE}/ws/rest/v1/{path.lstrip('/')}"
    with httpx.Client(timeout=30.0) as c:
        resp = c.get(url, params=params or {}, headers={"Authorization": _auth_header(), "Accept": "application/json"})
        resp.raise_for_status()
    return resp.json()


def _rest_post(path: str, payload: dict) -> dict:
    url = f"{_REST_BASE}/ws/rest/v1/{path.lstrip('/')}"
    with httpx.Client(timeout=30.0) as c:
        resp = c.post(url, json=payload, headers={
            "Authorization": _auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        resp.raise_for_status()
    return resp.json()


def _get_uuid(entity: str, name: str) -> Optional[str]:
    """Search for an entity by name, return first result UUID or None."""
    if not name:
        return None
    try:
        data = _rest_get(entity, params={"q": name})
        results = data.get("results", [])
        if results:
            return results[0].get("uuid")
        logger.warning("No %s found with name '%s'", entity, name)
    except Exception as exc:
        logger.warning("UUID lookup failed for %s '%s': %s", entity, name, exc)
    return None


class OpenMRSNoteWriterAgent:
    name = "OpenMRSNoteWriterAgent"
    version = "2.0.0"
    description = (
        "Writes encounter + all clinical entities to OpenMRS via REST API "
        "with dynamic concept UUID resolution."
    )

    # ── Encounter ─────────────────────────────────────────────────────────

    _VISIT_TYPE_NAME = "OPD Visit"

    def create_encounter(
        self,
        patient_uuid: str,
        visit_ts: str,
        encounter_type_name: str = "Consultation",
        location_uuid: Optional[str] = None,
        provider_uuid: Optional[str] = None,
        encounter_role_name: str = "Unknown",
    ) -> str:
        if settings.OPENMRS_SIMULATE:
            sim = f"sim-enc-{_uuid.uuid4()}"
            logger.info("Simulating encounter → %s", sim)
            return sim

        enc_type_uuid = _get_uuid("encountertype", encounter_type_name)
        loc_uuid      = location_uuid or settings.OPENMRS_DEFAULT_LOCATION_UUID
        prov_uuid     = provider_uuid or settings.OPENMRS_DEFAULT_PRACTITIONER_UUID
        enc_role_uuid = _get_uuid("encounterrole", encounter_role_name)

        if not enc_type_uuid:
            raise RuntimeError(f"Encounter type '{encounter_type_name}' not found in OpenMRS.")

        # Create a Visit first so the encounter appears in the Visits tab
        visit_uuid = self._create_visit(patient_uuid, visit_ts, loc_uuid)

        payload: dict[str, Any] = {
            "encounterDatetime": visit_ts,
            "patient":           patient_uuid,
            "encounterType":     enc_type_uuid,
            "location":          loc_uuid,
        }
        if visit_uuid:
            payload["visit"] = visit_uuid
        if prov_uuid and enc_role_uuid:
            payload["encounterProviders"] = [
                {"provider": prov_uuid, "encounterRole": enc_role_uuid}
            ]

        data = _rest_post("encounter", payload)
        enc_uuid = data.get("uuid")
        if not enc_uuid:
            raise RuntimeError(f"OpenMRS did not return encounter UUID. Response: {data}")
        logger.info("Encounter created → %s (visit → %s)", enc_uuid, visit_uuid)
        return enc_uuid

    def _create_visit(
        self,
        patient_uuid: str,
        visit_ts: str,
        location_uuid: Optional[str] = None,
    ) -> Optional[str]:
        """Create an OPD Visit so the encounter is visible in the Visits tab."""
        try:
            visit_type_uuid = _get_uuid("visittype", self._VISIT_TYPE_NAME)
            if not visit_type_uuid:
                logger.warning("Visit type '%s' not found — encounter will have no visit", self._VISIT_TYPE_NAME)
                return None

            payload: dict[str, Any] = {
                "patient":       patient_uuid,
                "visitType":     visit_type_uuid,
                "startDatetime": visit_ts,
            }
            if location_uuid:
                payload["location"] = location_uuid

            data = _rest_post("visit", payload)
            visit_uuid = data.get("uuid")
            logger.info("Visit created → %s", visit_uuid)
            return visit_uuid
        except Exception as exc:
            logger.warning("Visit creation failed (non-fatal): %s", exc)
            return None

    # ── Clinical-note Observation (REST) ─────────────────────────────────
    # CIEL concept 162169 = "Text of encounter note" (accepts free text)
    _SOAP_CONCEPT = "162169AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    def create_soap_observation(
        self,
        patient_uuid: str,
        encounter_uuid: str,
        soap_text: str,
        obs_datetime: str,
    ) -> str:
        if settings.OPENMRS_SIMULATE:
            sim = f"sim-obs-{_uuid.uuid4()}"
            logger.info("Simulating SOAP observation → %s", sim)
            return sim

        data = _rest_post("obs", {
            "person":      patient_uuid,
            "concept":     self._SOAP_CONCEPT,
            "obsDatetime": obs_datetime,
            "encounter":   encounter_uuid,
            "value":       soap_text,
        })
        obs_uuid = data.get("uuid")
        if not obs_uuid:
            raise RuntimeError(f"OpenMRS did not return SOAP obs UUID. Response: {data}")
        logger.info("SOAP observation → %s", obs_uuid)
        return obs_uuid

    # ── SOAP PDF attachment ───────────────────────────────────────────────

    @staticmethod
    def _safe(text: str) -> str:
        """Replace characters outside Latin-1 range so Helvetica renders cleanly."""
        replacements = {"—": "-", "–": "-", "’": "'", "‘": "'",
                        "“": '"', "”": '"', "•": "*", "°": " deg"}
        for ch, sub in replacements.items():
            text = text.replace(ch, sub)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    def generate_soap_pdf(
        self,
        patient_name: str,
        patient_id: str,
        visit_date: str,
        subjective: str,
        objective: str,
        assessment: str,
        plan: str,
    ) -> bytes:
        """Render the SOAP note as a PDF and return raw bytes."""
        from fpdf import FPDF

        s = self._safe

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Header
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "ScribeGuard Clinical Note", ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, s(f"Patient: {patient_name}  |  ID: {patient_id}  |  Date: {visit_date[:10]}"), ln=True, align="C")
        pdf.ln(4)
        pdf.set_draw_color(180, 180, 180)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(6)

        sections = [
            ("SUBJECTIVE",  subjective),
            ("OBJECTIVE",   objective),
            ("ASSESSMENT",  assessment),
            ("PLAN",        plan),
        ]
        for title, body in sections:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 8, title, ln=True, fill=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.ln(2)
            for line in (body or "").splitlines():
                pdf.multi_cell(0, 5, s(line) or " ")
            pdf.ln(4)

        # Footer
        pdf.set_y(-20)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 5, "Generated by ScribeGuard - Physician approved", align="C")

        return bytes(pdf.output())

    def upload_soap_attachment(
        self,
        patient_uuid: str,
        encounter_uuid: str,
        pdf_bytes: bytes,
        caption: str,
    ) -> Optional[str]:
        """Upload a PDF to OpenMRS attachment module."""
        if settings.OPENMRS_SIMULATE:
            sim = f"sim-att-{_uuid.uuid4()}"
            logger.info("Simulating SOAP attachment → %s", sim)
            return sim

        import base64
        url = f"{_REST_BASE}/ws/rest/v1/attachment"
        token = base64.b64encode(
            f"{settings.OPENMRS_USER}:{settings.OPENMRS_PASSWORD}".encode()
        ).decode()

        with httpx.Client(timeout=30.0) as c:
            resp = c.post(
                url,
                headers={"Authorization": f"Basic {token}"},
                data={
                    "patient":      patient_uuid,
                    "encounter":    encounter_uuid,
                    "fileCaption":  caption,
                },
                files={"file": (f"{caption}.pdf", pdf_bytes, "application/pdf")},
            )
            resp.raise_for_status()

        att_uuid = resp.json().get("uuid")
        logger.info("SOAP PDF attachment → %s", att_uuid)
        return att_uuid

    # ── Vital signs (REST obs) ────────────────────────────────────────────

    def create_vital(
        self,
        patient_uuid: str,
        encounter_uuid: str,
        kind: str,
        value: float,
        obs_datetime: str,
    ) -> Optional[str]:
        concept_name = _VITAL_CONCEPT_NAME.get(kind)
        if not concept_name:
            logger.warning("No concept mapping for vital kind '%s' — skipping", kind)
            return None

        if settings.OPENMRS_SIMULATE:
            return f"sim-vit-{_uuid.uuid4()}"

        concept_uuid = _get_uuid("concept", concept_name)
        if not concept_uuid:
            logger.warning("Concept '%s' not found — skipping vital %s", concept_name, kind)
            return None

        data = _rest_post("obs", {
            "person":      patient_uuid,
            "concept":     concept_uuid,
            "obsDatetime": obs_datetime,
            "encounter":   encounter_uuid,
            "value":       value,
        })
        obs_uuid = data.get("uuid")
        logger.info("Vital %s → obs %s", kind, obs_uuid)
        return obs_uuid

    # ── Allergies (REST) ──────────────────────────────────────────────────

    def create_allergy(
        self,
        patient_uuid: str,
        substance: str,
        reaction: Optional[str],
        severity: Optional[str],
        category: Optional[str],
    ) -> Optional[str]:
        if settings.OPENMRS_SIMULATE:
            return f"sim-alg-{_uuid.uuid4()}"

        allergen_type = _ALLERGY_TYPE.get((category or "medication").lower(), "DRUG")
        allergen_uuid = _get_uuid("concept", substance)

        # Use the "Other non-coded" concept (5622) when substance has no concept
        non_coded: Optional[str] = None
        if not allergen_uuid:
            allergen_uuid = "5622AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            non_coded = substance

        sev_name     = _SEVERITY_CONCEPT.get((severity or "moderate").lower(), "Moderate")
        severity_uuid = _get_uuid("concept", sev_name)

        payload: dict[str, Any] = {
            "allergen": {
                "allergenType":   allergen_type,
                "codedAllergen":  {"uuid": allergen_uuid},
            },
            "comment": reaction or "",
        }
        if non_coded:
            payload["allergen"]["nonCodedAllergen"] = non_coded
        if severity_uuid:
            payload["severity"] = {"uuid": severity_uuid}
        if reaction:
            reaction_uuid = _get_uuid("concept", reaction)
            if reaction_uuid:
                payload["reactions"] = [{"reaction": {"uuid": reaction_uuid}}]

        # Duplicate check
        try:
            existing = _rest_get(f"patient/{patient_uuid}/allergy").get("results", [])
            for a in existing:
                coded = a.get("allergen", {}).get("codedAllergen", {}).get("uuid", "")
                non   = a.get("allergen", {}).get("nonCodedAllergen", "")
                if coded == allergen_uuid or (non_coded and non.lower() == non_coded.lower()):
                    logger.info("Allergy '%s' already exists — skipping", substance)
                    return a.get("uuid")
        except Exception:
            pass

        data = _rest_post(f"patient/{patient_uuid}/allergy", payload)
        allergy_uuid = data.get("uuid")
        logger.info("Allergy '%s' → %s", substance, allergy_uuid)
        return allergy_uuid

    # ── Conditions (REST) ─────────────────────────────────────────────────

    def create_condition(
        self,
        patient_uuid: str,
        description: str,
        icd10_code: Optional[str],
        clinical_status: Optional[str],
        onset_datetime: Optional[str],
    ) -> Optional[str]:
        if settings.OPENMRS_SIMULATE:
            return f"sim-cnd-{_uuid.uuid4()}"

        concept_uuid = self._resolve_condition_concept(description, icd10_code)
        if not concept_uuid:
            logger.warning("No concept found for condition '%s' — skipping", description)
            return None

        status_map = {"active": "ACTIVE", "inactive": "INACTIVE", "resolved": "HISTORY_OF"}
        cs = status_map.get((clinical_status or "active").lower(), "ACTIVE")

        payload: dict[str, Any] = {
            "patient":            patient_uuid,
            "condition":          {"coded": concept_uuid},
            "clinicalStatus":     cs,
            "verificationStatus": "CONFIRMED",
        }
        if onset_datetime:
            payload["onsetDate"] = onset_datetime

        data = _rest_post("condition", payload)
        cond_uuid = data.get("uuid")
        logger.info("Condition '%s' → %s", description, cond_uuid)
        return cond_uuid

    # ── Medications / Drug orders (REST) ──────────────────────────────────

    def create_medication_order(
        self,
        patient_uuid: str,
        encounter_uuid: str,
        drug_name: str,
        dose: Optional[str],
        route: Optional[str],
        frequency: Optional[str],
        duration: Optional[str],
    ) -> Optional[str]:
        if settings.OPENMRS_SIMULATE:
            return f"sim-mrx-{_uuid.uuid4()}"

        # Duplicate check
        if self._medication_exists(patient_uuid, drug_name):
            logger.info("Medication '%s' already active — skipping", drug_name)
            return None

        # Drug lookup with progressive name fallback
        drug_uuid, concept_uuid = self._resolve_drug(drug_name)
        if not drug_uuid or not concept_uuid:
            return None

        # Parse dose into number + unit name
        dose_num, dose_unit_name = self._parse_dose(dose)

        # Dose units — expand abbreviations before searching
        dose_units_uuid: Optional[str] = None
        if dose_unit_name:
            canonical = _DOSE_UNIT_ALIAS.get(dose_unit_name, dose_unit_name)
            dose_units_uuid = _get_uuid("concept", canonical)

        # Route concept
        route_uuid = _get_uuid("concept", route) if route else None

        # Frequency via orderfrequency endpoint; default to "Once daily" when absent
        freq_search  = frequency or "Once daily"
        frequency_uuid = self._get_order_frequency(freq_search)
        if not frequency_uuid:
            frequency_uuid = self._get_order_frequency("Once daily")

        # Care setting + orderer
        care_setting_uuid = _get_uuid("caresetting", "Outpatient")
        orderer_uuid      = _get_uuid("provider", settings.OPENMRS_USER)

        # Hard requirements
        missing = {k: v for k, v in {
            "dose_units":   dose_units_uuid,
            "frequency":    frequency_uuid,
            "care_setting": care_setting_uuid,
            "orderer":      orderer_uuid,
        }.items() if v is None}
        if missing:
            logger.warning("Medication '%s' missing UUIDs %s — skipping", drug_name, list(missing.keys()))
            return None

        payload: dict[str, Any] = {
            "type":          "drugorder",
            "patient":       patient_uuid,
            "encounter":     encounter_uuid,
            "orderer":       orderer_uuid,
            "careSetting":   care_setting_uuid,
            "drug":          drug_uuid,
            "concept":       concept_uuid,
            "dose":          dose_num or 1,
            "doseUnits":     dose_units_uuid,
            "quantity":      dose_num or 1,
            "quantityUnits": dose_units_uuid,
            "frequency":     frequency_uuid,
            "numRefills":    0,
        }
        if route_uuid:
            payload["route"] = route_uuid

        # Duration (optional)
        if duration:
            dur_num, dur_unit = self._parse_dose(duration)
            if dur_unit:
                canonical_dur = _DOSE_UNIT_ALIAS.get(dur_unit, dur_unit)
                dur_unit_uuid = _get_uuid("concept", canonical_dur)
                if dur_num and dur_unit_uuid:
                    payload["duration"]      = dur_num
                    payload["durationUnits"] = dur_unit_uuid

        try:
            data = _rest_post("order", payload)
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            if "cannot.have.more.than.one" in body:
                logger.info("Medication '%s' already exists — skipping", drug_name)
                return None
            raise

        order_uuid = data.get("uuid")
        logger.info("Medication order '%s' → %s", drug_name, order_uuid)
        return order_uuid

    # ── Follow-up appointments ────────────────────────────────────────────
    _FOLLOWUP_SERVICE_NAME = "General Follow-up"

    def create_appointment(
        self,
        patient_uuid: str,
        description: str,
        interval: Optional[str],
        target_date: Optional[str],
        visit_ts: str,
    ) -> Optional[str]:
        if settings.OPENMRS_SIMULATE:
            return f"sim-appt-{_uuid.uuid4()}"

        # Resolve (or create) the follow-up service
        service_uuid = self._get_or_create_followup_service()
        if not service_uuid:
            logger.warning("No appointment service found — skipping follow-up '%s'", description)
            return None

        # Compute appointment datetime
        appt_dt = self._resolve_appointment_date(visit_ts, interval, target_date)

        end_dt = self._add_minutes(appt_dt, 30)

        payload: dict[str, Any] = {
            "patientUuid":      patient_uuid,
            "serviceUuid":      service_uuid,
            "startDateTime":    appt_dt,
            "endDateTime":      end_dt,
            "appointmentKind":  "Scheduled",
            "status":           "Scheduled",
            "comments":         self._safe(f"{description}{' (' + interval + ')' if interval else ''}"),
        }

        data = _rest_post("appointments", payload)
        appt_uuid = data.get("uuid")
        logger.info("Appointment '%s' → %s (start: %s)", description[:40], appt_uuid, appt_dt)
        return appt_uuid

    def _get_or_create_followup_service(self) -> Optional[str]:
        """Return the General Follow-up service UUID from config, creating it if absent."""
        # Use preconfigured UUID when available (avoids the broken LIST endpoint)
        if settings.OPENMRS_FOLLOWUP_SERVICE_UUID:
            return settings.OPENMRS_FOLLOWUP_SERVICE_UUID

        # Fallback: create the service and expect caller to persist the UUID to config
        try:
            resp = _rest_post("appointmentService", {
                "name":         self._FOLLOWUP_SERVICE_NAME,
                "description":  "General outpatient follow-up appointments",
                "durationMins": 30,
                "color":        "#006EFF",
                "startTime":    "08:00:00",
                "endTime":      "17:00:00",
            })
            svc_uuid = resp.get("uuid")
            logger.info("Created appointment service '%s' → %s (add to OPENMRS_FOLLOWUP_SERVICE_UUID in .env)", self._FOLLOWUP_SERVICE_NAME, svc_uuid)
            return svc_uuid
        except Exception as exc:
            logger.warning("Appointment service create failed: %s", exc)
            return None

    @staticmethod
    def _resolve_appointment_date(
        visit_ts: str,
        interval: Optional[str],
        target_date: Optional[str],
    ) -> str:
        """
        Convert an interval like '6 weeks' or 'within one week' into an ISO
        datetime string. Falls back to 4 weeks from visit_ts if unparseable.
        """
        from datetime import datetime, timezone, timedelta
        import re

        # Prefer an explicit target date
        if target_date:
            try:
                dt = datetime.fromisoformat(target_date.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%dT00:00:00.000+0000")
            except ValueError:
                pass

        # Parse interval string
        try:
            base = datetime.fromisoformat(visit_ts.replace("Z", "+00:00"))
        except ValueError:
            base = datetime.now(timezone.utc)

        days = 28  # default: 4 weeks
        if interval:
            text = interval.lower()
            # word numbers
            word_map = {"one": 1, "two": 2, "three": 3, "four": 4,
                        "five": 5, "six": 6, "seven": 7, "eight": 8}
            for word, num in word_map.items():
                text = text.replace(word, str(num))
            m = re.search(r"(\d+)\s*(day|week|month|year)", text)
            if m:
                n, unit = int(m.group(1)), m.group(2)
                days = {"day": n, "week": n * 7, "month": n * 30, "year": n * 365}[unit]

        appt = base + timedelta(days=days)
        return appt.strftime("%Y-%m-%dT00:00:00.000+0000")

    @staticmethod
    def _add_minutes(dt_str: str, minutes: int) -> str:
        from datetime import datetime, timedelta
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.000+0000")
        return (dt + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S.000+0000")



    # ── Helpers ───────────────────────────────────────────────────────────

    def _resolve_drug(self, drug_name: str) -> tuple[Optional[str], Optional[str]]:
        """
        Look up drug UUID + its concept UUID by name with progressive fallback.
        Returns (drug_uuid, concept_uuid) or (None, None) if not found.
        """
        words = drug_name.split()
        candidates = [drug_name] + [" ".join(words[:n]) for n in range(len(words) - 1, 0, -1)]
        for name in candidates:
            drug_uuid = _get_uuid("drug", name)
            if drug_uuid:
                try:
                    drug_data    = _rest_get(f"drug/{drug_uuid}")
                    concept_uuid = drug_data.get("concept", {}).get("uuid")
                    if concept_uuid:
                        if name != drug_name:
                            logger.info("Drug '%s' matched on '%s'", drug_name, name)
                        return drug_uuid, concept_uuid
                except Exception:
                    pass
        logger.warning("Drug '%s' not found in OpenMRS — skipping", drug_name)
        return None, None

    def _get_order_frequency(self, frequency: str) -> Optional[str]:
        """Look up a drug order frequency UUID via the orderfrequency endpoint."""
        try:
            data = _rest_get("orderfrequency", params={"q": frequency})
            results = data.get("results", [])
            if results:
                return results[0].get("uuid")
        except Exception as exc:
            logger.warning("Order frequency lookup failed for '%s': %s", frequency, exc)
        return None

    def _resolve_condition_concept(
        self, description: str, icd10_code: Optional[str]
    ) -> Optional[str]:
        """
        Try progressively shorter searches to find a matching OpenMRS concept.

        Order:
          1. Exact full description
          2. ICD-10 code (e.g. "I15.0")
          3. First N words of description (N = len-1 down to 2)
          4. First word alone
        """
        # 1. Full description
        uid = _get_uuid("concept", description)
        if uid:
            return uid

        # 2. ICD-10 code
        if icd10_code:
            uid = _get_uuid("concept", icd10_code)
            if uid:
                return uid

        # 3–4. Progressive word truncation
        words = description.split()
        for n in range(len(words) - 1, 0, -1):
            shorter = " ".join(words[:n])
            uid = _get_uuid("concept", shorter)
            if uid:
                logger.info(
                    "Condition '%s' matched on shortened term '%s'", description, shorter
                )
                return uid

        return None

    def _medication_exists(self, patient_uuid: str, drug_name: str) -> bool:
        try:
            data = _rest_get("order", params={"patient": patient_uuid})
            for order in data.get("results", []):
                if drug_name.lower() in order.get("display", "").lower() and order.get("action") == "NEW":
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def _parse_dose(dose_str: Optional[str]) -> tuple[Optional[float], Optional[str]]:
        """Split '4 mg' → (4.0, 'mg'), '125 mL' → (125.0, 'mL')."""
        import re
        if not dose_str:
            return None, None
        m = re.match(r"(\d+(?:\.\d+)?)\s*(.*)", dose_str.strip())
        if m:
            num  = float(m.group(1))
            unit = m.group(2).strip() or None
            return (int(num) if num.is_integer() else num), unit
        return None, dose_str.strip() or None
