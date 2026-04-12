"""
All environment configuration and shared constants for the OpenMRS FHIR R4 module.

Set these in your .env file at the backend root:
    FHIR_SERVER=http://localhost:8080/openmrs/ws/fhir2/R4
    OPENMRS_USER=Admin
    OPENMRS_PASSWORD=Admin123
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Server connection
# ---------------------------------------------------------------------------
FHIR_SERVER  = os.getenv("FHIR_SERVER",      "http://localhost:8080/openmrs/ws/fhir2/R4")
FHIR_USER    = os.getenv("OPENMRS_USER",      "Admin")
FHIR_PASS    = os.getenv("OPENMRS_PASSWORD",  "Admin123")

# ---------------------------------------------------------------------------
# (replace with your sandbox's actual UUIDs if different)
# ---------------------------------------------------------------------------
DEFAULT_PATIENT_UUID      = "ebc1de10-e41d-4540-8113-e2dfaaff77e8"
DEFAULT_PRACTITIONER_UUID = "f9badd80-ab76-11e2-9e96-0800200c9a66"
DEFAULT_SUPER_USER_UUID   = "4bcd741a-b0f8-4c30-8a73-8c6e33575ff9"
DEFAULT_LOCATION_UUID     = "8d6c993e-c2cc-11de-8d13-0010c6dffd0f"
DEFAULT_MEDICATION_UUID   = "fbf74fd6-b37c-4325-86cb-dcaf4aabed81"

# ---------------------------------------------------------------------------
# CIEL concept codes used in Observation resources
# ---------------------------------------------------------------------------
CONCEPT = {
    "height":      "5090AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "weight":      "5089AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "temperature": "5088AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "resp_rate":   "5242AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "spo2":        "5092AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
}