"""
Agent registry — a single mapping from `name → Agent instance`.

Keeping construction in one place lets the orchestrator (and tests) swap
real agents for fakes without changing the call sites.
"""
from __future__ import annotations

from typing import Iterable, Optional

from app.agents import Agent


class AgentRegistry:
    def __init__(self, agents: Iterable[Agent] = ()):
        self._agents: dict[str, Agent] = {}
        for a in agents:
            self.register(a)

    def register(self, agent: Agent) -> None:
        self._agents[agent.name] = agent

    def register_alias(self, alias: str, agent: Agent) -> None:
        """Register a second name pointing to the same agent instance.

        Useful for keeping backward-compatible names while we evolve the
        canonical agent set.
        """
        self._agents[alias] = agent

    def get(self, name: str) -> Optional[Agent]:
        return self._agents.get(name)

    def require(self, name: str) -> Agent:
        agent = self.get(name)
        if agent is None:
            raise KeyError(f"Agent '{name}' is not registered")
        return agent

    def all(self) -> list[Agent]:
        return list(self._agents.values())


def build_default_registry() -> AgentRegistry:
    """Construct the production registry with all 7 specialized agents.

    The classification step is `ClinicalEntityExtractionAgent` which
    populates medications, allergies, conditions, vital signs, and
    follow-ups in a single pass. It is also registered under its legacy
    `MedicationExtractionAgent` alias so external integrations using the
    old name continue to work.
    """
    # Imports are local to avoid circular imports during module init.
    from app.agents.intake import EncounterIntakeAgent
    from app.agents.transcription import TranscriptionAgent
    from app.agents.note_generation import ClinicalNoteGenerationAgent
    from app.agents.clinical_extraction import ClinicalEntityExtractionAgent
    from app.agents.physician_review import PhysicianReviewAgent
    from app.agents.openmrs.integration import OpenMRSIntegrationAgent
    from app.agents.audit import AuditTraceabilityAgent

    classifier = ClinicalEntityExtractionAgent()

    registry = AgentRegistry([
        EncounterIntakeAgent(),
        TranscriptionAgent(),
        ClinicalNoteGenerationAgent(),
        classifier,
        PhysicianReviewAgent(),
        OpenMRSIntegrationAgent(),
        AuditTraceabilityAgent(),
    ])
    # Legacy alias used by older callers and the orchestrator pipeline name.
    registry.register_alias("MedicationExtractionAgent", classifier)
    return registry
