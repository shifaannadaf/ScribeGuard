"""
OpenMRSNoteWriterAgent — performs the actual FHIR writes (Encounter,
Observations, AllergyIntolerance, Condition, MedicationRequest).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.config import settings


logger = logging.getLogger("scribeguard.agents.openmrs.note_writer")


class OpenMRSNoteWriterAgent:
    name = "OpenMRSNoteWriterAgent"
    version = "1.1.0"
    description = "Writes the encounter + clinical-note observation + entities into OpenMRS."

    # ── Encounter ─────────────────────────────────────────────────────

    def create_encounter(self, encounter_payload: dict[str, Any]) -> str:
        if settings.OPENMRS_SIMULATE:
            simulated = f"sim-enc-{uuid.uuid4()}"
            logger.info("Simulating OpenMRS encounter create → %s", simulated)
            return simulated
        from app.openmrs.client import fhir_post
        data = fhir_post("Encounter", encounter_payload)
        enc_uuid = data.get("id")
        if not enc_uuid:
            raise RuntimeError("OpenMRS did not return an Encounter UUID.")
        return enc_uuid

    # ── Observation (note + vitals) ──────────────────────────────────

    def create_observation(self, observation_payload: dict[str, Any]) -> str:
        if settings.OPENMRS_SIMULATE:
            simulated = f"sim-obs-{uuid.uuid4()}"
            logger.info("Simulating OpenMRS observation create → %s", simulated)
            return simulated
        from app.openmrs.client import fhir_post
        data = fhir_post("Observation", observation_payload)
        obs_uuid = data.get("id")
        if not obs_uuid:
            raise RuntimeError("OpenMRS did not return an Observation UUID.")
        return obs_uuid

    # ── AllergyIntolerance ───────────────────────────────────────────

    def create_allergy(self, payload: dict[str, Any]) -> str:
        if settings.OPENMRS_SIMULATE:
            return f"sim-alg-{uuid.uuid4()}"
        from app.openmrs.client import fhir_post
        data = fhir_post("AllergyIntolerance", payload)
        return data.get("id") or ""

    # ── Condition ────────────────────────────────────────────────────

    def create_condition(self, payload: dict[str, Any]) -> str:
        if settings.OPENMRS_SIMULATE:
            return f"sim-cnd-{uuid.uuid4()}"
        from app.openmrs.client import fhir_post
        data = fhir_post("Condition", payload)
        return data.get("id") or ""

    # ── MedicationRequest ────────────────────────────────────────────

    def create_medication_request(self, payload: dict[str, Any]) -> str:
        if settings.OPENMRS_SIMULATE:
            return f"sim-mrx-{uuid.uuid4()}"
        from app.openmrs.client import fhir_post
        data = fhir_post("MedicationRequest", payload)
        return data.get("id") or ""
