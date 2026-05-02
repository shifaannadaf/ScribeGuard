"""OpenMRS submission schemas."""
from typing import Optional
from pydantic import BaseModel


class SubmitRequest(BaseModel):
    openmrs_patient_uuid: Optional[str] = None
    practitioner_uuid:    Optional[str] = None
    actor:                str           = "physician"


class SubmitResponse(BaseModel):
    encounter_id: str
    submission_id: int
    status: str
    openmrs_encounter_uuid: Optional[str] = None
    openmrs_observation_uuid: Optional[str] = None
    attempts: int
    error: Optional[str] = None
