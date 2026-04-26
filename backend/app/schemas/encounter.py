from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.models import EncounterStatus


class MedicationIn(BaseModel):
    id:         Optional[int] = None
    name:       str
    dose:       Optional[str] = None
    route:      Optional[str] = None
    frequency:  Optional[str] = None
    start_date: Optional[str] = None


class MedicationOut(MedicationIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AllergyIn(BaseModel):
    id:       Optional[int] = None
    allergen: str
    reaction: Optional[str] = None
    severity: Optional[str] = None


class AllergyOut(AllergyIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DiagnosisIn(BaseModel):
    id:          Optional[int] = None
    icd10_code:  Optional[str] = None
    description: str
    status:      Optional[str] = None


class DiagnosisOut(DiagnosisIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class EncounterListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:           str
    patient_name: str
    patient_id:   str
    date:         str
    time:         str
    duration:     Optional[str] = None
    status:       EncounterStatus
    snippet:      Optional[str] = None


class EncounterListResponse(BaseModel):
    data: list[EncounterListItem]


class EncounterDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:           str
    patient_name: str
    patient_id:   str
    openmrs_uuid: Optional[str]       = None
    duration:     Optional[str]       = None
    status:       EncounterStatus
    transcript:   Optional[str]       = None
    created_at:   datetime
    updated_at:   datetime
    medications:  list[MedicationOut] = []
    allergies:    list[AllergyOut]    = []
    diagnoses:    list[DiagnosisOut]  = []


class EncounterCreateResponse(BaseModel):
    id:           str
    patient_name: str
    patient_id:   str
    status:       EncounterStatus
    created_at:   datetime


class EncounterUpdate(BaseModel):
    transcript:  Optional[str]              = None
    medications: Optional[list[MedicationIn]] = None
    allergies:   Optional[list[AllergyIn]]    = None
    diagnoses:   Optional[list[DiagnosisIn]]  = None


class EncounterStatusResponse(BaseModel):
    id:         str
    status:     EncounterStatus
    updated_at: datetime


class StatsResponse(BaseModel):
    notes_today:      int
    pending_review:   int
    pushed_to_openmrs: int
    total_transcripts: int
