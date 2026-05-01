"""
OpenMRSSubmissionVerifierAgent — verifies the write actually persisted by
performing a follow-up read.
"""
from __future__ import annotations

import logging
from typing import Any

from app.config import settings


logger = logging.getLogger("scribeguard.agents.openmrs.verifier")


class OpenMRSSubmissionVerifierAgent:
    name = "OpenMRSSubmissionVerifierAgent"
    version = "1.0.0"
    description = "Confirms the OpenMRS write succeeded by reading it back."

    def verify(self, *, encounter_uuid: str, observation_uuid: str) -> dict[str, Any]:
        if settings.OPENMRS_SIMULATE:
            logger.info("Verification SIMULATED for enc=%s obs=%s", encounter_uuid, observation_uuid)
            return {"simulated": True, "ok": True}

        from app.openmrs.client import fhir_get
        ok = True
        details: dict[str, Any] = {}
        try:
            details["observation"] = fhir_get(f"Observation/{observation_uuid}")
        except Exception as exc:  # noqa: BLE001
            ok = False
            details["observation_error"] = str(exc)
        return {"simulated": False, "ok": ok, **details}
