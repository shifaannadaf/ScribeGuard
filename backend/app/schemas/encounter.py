"""
Encounter API schemas.

Pydantic v2 schemas exposed by the encounter routes. The agent layer never
imports from here — everything inside agents flows through `agents.context`.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

from app.models.encounter import EncounterStatus, ProcessingStage


# ── Identity ────────────────────────────────────────────────────────────

class EncounterCreate(BaseModel):
    patient_name: str
    patient_id:   str
    openmrs_patient_uuid: Optional[str] = None


class EncounterCreated(BaseModel):
    id:           str
    patient_name: str
    patient_id:   str
    openmrs_patient_uuid: Optional[str] = None
    status:       EncounterStatus
    processing_stage: ProcessingStage
    created_at:   datetime


# ── Listing ─────────────────────────────────────────────────────────────

class EncounterListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           str
    patient_name: str
    patient_id:   str
    date:         str
    time:         str
    duration:     Optional[str]      = None
    status:       EncounterStatus
    processing_stage: ProcessingStage
    snippet:      Optional[str]      = None
    has_soap_note: bool              = False
    medication_count: int            = 0
    submitted: bool                  = False


class EncounterListResponse(BaseModel):
    data: List[EncounterListItem]


# ── Detail ─────────────────────────────────────────────────────────────

class TranscriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    raw_text: str
    formatted_text: Optional[str] = None
    duration_seconds: Optional[float] = None
    model: str
    quality_score: Optional[float] = None
    quality_issues: Optional[list] = None
    word_count: Optional[int] = None
    created_at: datetime


class SoapSectionsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version: int
    is_current: bool
    subjective: str
    objective:  str
    assessment: str
    plan:       str
    status:     str
    low_confidence_sections: Optional[list] = None
    flags: Optional[dict] = None
    model: str
    created_at: datetime
    updated_at: datetime


class MedicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    dose: Optional[str]      = None
    route: Optional[str]     = None
    frequency: Optional[str] = None
    duration: Optional[str]  = None
    start_date: Optional[str] = None
    indication: Optional[str] = None
    raw_text: Optional[str]   = None
    confidence: Optional[str] = None


class AllergyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    substance: str
    reaction: Optional[str] = None
    severity: Optional[str] = None
    category: Optional[str] = None
    onset:    Optional[str] = None
    confidence: Optional[str] = None
    raw_text: Optional[str] = None
    openmrs_resource_uuid: Optional[str] = None


class ConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    description: str
    icd10_code:  Optional[str] = None
    snomed_code: Optional[str] = None
    clinical_status: Optional[str] = None
    verification:    Optional[str] = None
    onset:           Optional[str] = None
    note:            Optional[str] = None
    confidence:      Optional[str] = None
    raw_text:        Optional[str] = None
    openmrs_resource_uuid: Optional[str] = None


class VitalSignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    value: float
    unit: Optional[str] = None
    measured_at: Optional[str] = None
    confidence:  Optional[str] = None
    raw_text:    Optional[str] = None
    openmrs_resource_uuid: Optional[str] = None


class FollowUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    description: str
    interval: Optional[str] = None
    target_date: Optional[str] = None
    with_provider: Optional[str] = None
    confidence: Optional[str] = None


class PatientContextOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fetched_at: datetime
    patient_uuid: Optional[str] = None
    patient_demographics: Optional[dict] = None
    existing_medications: Optional[list] = None
    existing_allergies:   Optional[list] = None
    existing_conditions:  Optional[list] = None
    recent_observations:  Optional[list] = None
    recent_encounters:    Optional[list] = None
    fetch_errors:         Optional[dict] = None


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    attempts: int
    openmrs_encounter_uuid: Optional[str] = None
    openmrs_observation_uuid: Optional[str] = None
    last_error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class EncounterDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           str
    patient_name: str
    patient_id:   str
    openmrs_patient_uuid: Optional[str] = None

    status:           EncounterStatus
    processing_stage: ProcessingStage
    last_error:       Optional[str] = None

    duration:           Optional[str] = None
    audio_filename:     Optional[str] = None
    audio_duration_sec: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    transcript:   Optional[TranscriptOut]   = None
    soap_note:    Optional[SoapSectionsOut] = None
    medications:  List[MedicationOut]       = []
    allergies:    List[AllergyOut]          = []
    conditions:   List[ConditionOut]        = []
    vital_signs:  List[VitalSignOut]        = []
    follow_ups:   List[FollowUpOut]         = []
    patient_context: Optional[PatientContextOut] = None
    submission:   Optional[SubmissionOut]   = None


# ── Stats ─────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    notes_today:       int
    pending_review:    int
    pushed_to_openmrs: int
    failed:            int
    total_encounters:  int
