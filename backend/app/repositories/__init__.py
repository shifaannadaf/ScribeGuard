"""Data access layer (repositories).

Agents call repositories instead of touching SQLAlchemy directly. This keeps
agent code focused on its responsibility and gives the persistence layer a
clear boundary we can swap out (e.g. for testing).
"""
from app.repositories.encounter_repo import EncounterRepository
from app.repositories.transcript_repo import TranscriptRepository
from app.repositories.soap_repo import SoapRepository
from app.repositories.medication_repo import MedicationRepository
from app.repositories.clinical_entity_repo import ClinicalEntityRepository
from app.repositories.submission_repo import SubmissionRepository
from app.repositories.agent_run_repo import AgentRunRepository
from app.repositories.audit_repo import AuditRepository

__all__ = [
    "EncounterRepository",
    "TranscriptRepository",
    "SoapRepository",
    "MedicationRepository",
    "ClinicalEntityRepository",
    "SubmissionRepository",
    "AgentRunRepository",
    "AuditRepository",
]
