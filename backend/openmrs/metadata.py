"""
FHIR R4 CapabilityStatement — server health check and feature discovery.

Endpoints used:
    GET /metadata   → returns the server's CapabilityStatement
"""

import logging
from .client import fhir_get

logger = logging.getLogger(__name__)


def get_metadata() -> dict:
    """
    READ — Fetch the FHIR CapabilityStatement.

    GET /metadata

    Returns a CapabilityStatement resource describing every FHIR resource
    type and operation the server supports. Useful for:
        - Verifying the server is alive before other calls
        - Discovering which resource types are available
        - Checking the FHIR version

    Example:
        meta = get_metadata()
        print(meta["fhirVersion"])   # e.g. "4.0.1"
        print(meta["software"]["name"])  # e.g. "OpenMRS FHIR2 Module"
    """
    data = fhir_get("metadata")
    logger.info("Fetched FHIR metadata — fhirVersion=%s", data.get("fhirVersion"))
    return data