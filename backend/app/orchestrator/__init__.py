"""
Agent orchestration layer.

The orchestrator coordinates the seven specialized agents end-to-end. It
owns:
    - state transitions on the encounter (ProcessingStage)
    - retries and exception handling
    - persistence of every AgentRun and AuditEvent
    - the public pipeline-execution API used by FastAPI routes
"""
from app.orchestrator.orchestrator import AgentOrchestrator
from app.orchestrator.registry import AgentRegistry, build_default_registry

__all__ = [
    "AgentOrchestrator",
    "AgentRegistry",
    "build_default_registry",
]
