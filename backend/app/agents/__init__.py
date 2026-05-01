"""
Agentic AI primitives for ScribeGuard.

Each agent is a self-contained, autonomous unit of clinical-workflow logic
with an explicit contract:

    class MyAgent(Agent[InputT, OutputT]):
        name = "MyAgent"
        async def run(self, ctx) -> AgentResult[OutputT]: ...

Agents are coordinated by the orchestrator (see app.orchestrator). Every
agent invocation produces a persisted AgentRun row plus an AuditEvent so
the entire end-to-end pipeline is observable and reproducible.
"""
from app.agents.base import Agent, AgentResult
from app.agents.context import AgentContext
from app.agents.exceptions import AgentError, AgentValidationError, AgentExecutionError

__all__ = [
    "Agent",
    "AgentResult",
    "AgentContext",
    "AgentError",
    "AgentValidationError",
    "AgentExecutionError",
]
