"""
DEPRECATED: backward-compat re-export shim.

The original monolithic models module has been split into one file per
aggregate (see app/models/__init__.py). New code should import from
`app.models` directly.
"""
from app.models import (
    Encounter,
    EncounterStatus,
    ProcessingStage,
    Transcript,
    SoapNote,
    SoapNoteStatus,
    Medication,
    PhysicianEdit,
    PhysicianApproval,
    SubmissionRecord,
    SubmissionStatus,
    AgentRun,
    AgentRunStatus,
    AuditEvent,
)

__all__ = [
    "Encounter",
    "EncounterStatus",
    "ProcessingStage",
    "Transcript",
    "SoapNote",
    "SoapNoteStatus",
    "Medication",
    "PhysicianEdit",
    "PhysicianApproval",
    "SubmissionRecord",
    "SubmissionStatus",
    "AgentRun",
    "AgentRunStatus",
    "AuditEvent",
]
