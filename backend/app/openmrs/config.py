"""
OpenMRS FHIR R4 module configuration.

These values are sourced from the central app.config.settings so the entire
application has one configuration source of truth. The constants below
remain importable for backward compatibility with the existing FHIR client
helpers in this directory.
"""
from app.config import settings


FHIR_SERVER  = settings.FHIR_SERVER
FHIR_USER    = settings.OPENMRS_USER
FHIR_PASS    = settings.OPENMRS_PASSWORD

# Default UUIDs for the OpenMRS Reference Application demo dataset.
DEFAULT_PATIENT_UUID      = "ebc1de10-e41d-4540-8113-e2dfaaff77e8"
DEFAULT_PRACTITIONER_UUID = settings.OPENMRS_DEFAULT_PRACTITIONER_UUID
DEFAULT_SUPER_USER_UUID   = "4bcd741a-b0f8-4c30-8a73-8c6e33575ff9"
DEFAULT_LOCATION_UUID     = settings.OPENMRS_DEFAULT_LOCATION_UUID
DEFAULT_MEDICATION_UUID   = "fbf74fd6-b37c-4325-86cb-dcaf4aabed81"
DEFAULT_ENCOUNTER_TYPE_UUID = "dd528487-82a5-4082-9c72-ed246bd49591"  # Consultation encounter type
DEFAULT_VISIT_TYPE_UUID     = "7b0f5697-27e3-40c4-8bae-f4049abfb4ed"  # Facility Visit
DEFAULT_CARE_SETTING_UUID   = "6f0c9a92-6f24-11e3-af88-005056821db0"  # Outpatient
DEFAULT_PROVIDER_UUID       = "e9a352fa-9dc8-45c0-a398-23e18f730ca2"  # admin/Super User provider
DEFAULT_QUANTITY_UNITS_UUID = "1513AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"  # Tablet (generic quantity unit)

# CIEL concept codes used in Observation resources
CONCEPT = {
    "height":      "5090AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "weight":      "5089AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "temperature": "5088AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "resp_rate":   "5242AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "spo2":        "5092AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
}
