from typing import Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role:    str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply:      str
    message_id: int


class OpenMRSPatient(BaseModel):
    uuid:                str
    name:                str
    identifier:          str
    birthdate:           Optional[str] = None
    gender:              Optional[str] = None
    active_medications:  list = []
    known_allergies:     list = []


class PushRequest(BaseModel):
    openmrs_patient_uuid: Optional[str] = None  # If None, creates new patient in OpenMRS


class PushResponse(BaseModel):
    id:           str
    status:       str
    openmrs_uuid: str
    pushed_at:    str


class TranscribeResponse(BaseModel):
    id:         str
    transcript: str
    duration:   str


class GenerateResponse(BaseModel):
    id:          str
    medications: list
    allergies:   list
    diagnoses:   list
