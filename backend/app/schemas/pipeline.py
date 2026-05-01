"""Pipeline / orchestration schemas."""
from datetime import datetime
from typing import Any, Optional, List
from pydantic import BaseModel, ConfigDict


class AgentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    agent_name: str
    agent_version: Optional[str] = None
    status: str
    attempt: int
    input_summary: Optional[Any] = None
    output_summary: Optional[Any] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[float] = None


class PipelineStatus(BaseModel):
    encounter_id: str
    processing_stage: str
    status: str
    last_error: Optional[str] = None
    has_audio: bool = False
    has_transcript: bool = False
    has_soap_note: bool = False
    has_approval: bool = False
    submitted: bool = False
    agent_runs: List[AgentRunOut] = []


class TranscribeResponse(BaseModel):
    encounter_id: str
    transcript_id: int
    text: str
    duration_seconds: Optional[float] = None
    quality_score: Optional[float] = None
    quality_issues: List[str] = []


class GenerateSoapResponse(BaseModel):
    encounter_id: str
    soap_note_id: int
    subjective: str
    objective:  str
    assessment: str
    plan:       str
    medications_extracted: int
    low_confidence_sections: List[str] = []


class RunPipelineResponse(BaseModel):
    encounter_id: str
    final_stage: str
    status: str
    transcript_id: Optional[int] = None
    soap_note_id: Optional[int] = None
    medications_extracted: int = 0
    duration_ms: float
    errors: List[str] = []
