"""
OpenMRSAuthAgent — verifies the OpenMRS FHIR R4 endpoint is reachable and
that our credentials work BEFORE we attempt any write.

Implementation: hits `GET /metadata` (a cheap CapabilityStatement read),
which fails fast on bad creds or a down sandbox.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings


logger = logging.getLogger("scribeguard.agents.openmrs.auth")


class OpenMRSAuthAgent:
    name = "OpenMRSAuthAgent"
    version = "1.0.0"
    description = "Verifies OpenMRS connectivity and authentication."

    def authenticate(self) -> dict[str, Any]:
        """Returns capability metadata on success, raises on failure."""
        if settings.OPENMRS_SIMULATE:
            logger.info("OpenMRS authentication SIMULATED (OPENMRS_SIMULATE=true)")
            return {
                "simulated":   True,
                "fhirVersion": "4.0.1",
                "server":      settings.FHIR_SERVER,
            }

        from app.openmrs.metadata import get_metadata
        try:
            data = get_metadata()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"OpenMRS auth/metadata call failed: {exc}") from exc

        return {
            "simulated":   False,
            "fhirVersion": data.get("fhirVersion"),
            "server":      settings.FHIR_SERVER,
        }
