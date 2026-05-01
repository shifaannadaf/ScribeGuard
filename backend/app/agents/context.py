"""
Shared context object passed into every agent.

Agents must NEVER receive a raw SQLAlchemy session out-of-band. Instead they
receive an `AgentContext` that bundles the session, the encounter being
processed, and the repositories they may operate on. This is the durable
seam that lets the orchestrator wire every agent uniformly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import Encounter
from app.repositories import (
    EncounterRepository,
    TranscriptRepository,
    SoapRepository,
    MedicationRepository,
    ClinicalEntityRepository,
    SubmissionRepository,
    AgentRunRepository,
    AuditRepository,
)


@dataclass
class AgentContext:
    db: Session
    encounter: Encounter
    actor: str = "system"
    payload: dict[str, Any] = field(default_factory=dict)

    # Repository handles — created lazily from the same session
    _encounter_repo: Optional[EncounterRepository] = None
    _transcript_repo: Optional[TranscriptRepository] = None
    _soap_repo: Optional[SoapRepository] = None
    _med_repo: Optional[MedicationRepository] = None
    _entity_repo: Optional[ClinicalEntityRepository] = None
    _submission_repo: Optional[SubmissionRepository] = None
    _agent_run_repo: Optional[AgentRunRepository] = None
    _audit_repo: Optional[AuditRepository] = None

    @property
    def encounter_id(self) -> str:
        return self.encounter.id

    @property
    def encounters(self) -> EncounterRepository:
        if self._encounter_repo is None:
            self._encounter_repo = EncounterRepository(self.db)
        return self._encounter_repo

    @property
    def transcripts(self) -> TranscriptRepository:
        if self._transcript_repo is None:
            self._transcript_repo = TranscriptRepository(self.db)
        return self._transcript_repo

    @property
    def soap_notes(self) -> SoapRepository:
        if self._soap_repo is None:
            self._soap_repo = SoapRepository(self.db)
        return self._soap_repo

    @property
    def medications(self) -> MedicationRepository:
        if self._med_repo is None:
            self._med_repo = MedicationRepository(self.db)
        return self._med_repo

    @property
    def entities(self) -> ClinicalEntityRepository:
        if self._entity_repo is None:
            self._entity_repo = ClinicalEntityRepository(self.db)
        return self._entity_repo

    @property
    def submissions(self) -> SubmissionRepository:
        if self._submission_repo is None:
            self._submission_repo = SubmissionRepository(self.db)
        return self._submission_repo

    @property
    def agent_runs(self) -> AgentRunRepository:
        if self._agent_run_repo is None:
            self._agent_run_repo = AgentRunRepository(self.db)
        return self._agent_run_repo

    @property
    def audit(self) -> AuditRepository:
        if self._audit_repo is None:
            self._audit_repo = AuditRepository(self.db)
        return self._audit_repo
