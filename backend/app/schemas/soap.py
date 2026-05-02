"""SOAP note edit / approve schemas."""
from typing import Optional, List
from pydantic import BaseModel


class SoapSectionEdit(BaseModel):
    subjective: Optional[str] = None
    objective:  Optional[str] = None
    assessment: Optional[str] = None
    plan:       Optional[str] = None


class MedicationEdit(BaseModel):
    id: Optional[int]        = None
    name: str
    dose: Optional[str]      = None
    route: Optional[str]     = None
    frequency: Optional[str] = None
    duration: Optional[str]  = None
    start_date: Optional[str] = None
    indication: Optional[str] = None


class SoapEditRequest(BaseModel):
    sections:    Optional[SoapSectionEdit] = None
    medications: Optional[List[MedicationEdit]] = None
    actor:       str = "physician"


class SoapApproveRequest(BaseModel):
    actor:    str           = "physician"
    comments: Optional[str] = None


class SoapApproveResponse(BaseModel):
    encounter_id: str
    soap_note_id: int
    approved_at:  str
    edits_made:   int
