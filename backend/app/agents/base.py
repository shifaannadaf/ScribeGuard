"""
Base agent contract.

Every specialized agent in ScribeGuard inherits from `Agent`. The base class
is intentionally minimal — agents are autonomous units that:

    - declare a `name` and `version`
    - define a `description`
    - implement `run(ctx)` which returns an `AgentResult`

Cross-cutting concerns (retry, persistence of agent runs, audit emission,
state transitions) live in the orchestrator, NOT in agents themselves. This
keeps each agent file focused and testable in isolation.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Generic, Optional, TypeVar

from app.agents.context import AgentContext


T = TypeVar("T")


@dataclass
class AgentResult(Generic[T]):
    """Structured agent output the orchestrator persists as `output_summary`."""
    success: bool
    output: Optional[T] = None
    summary: dict[str, Any] = field(default_factory=dict)
    next_stage_hint: Optional[str] = None


class Agent(abc.ABC, Generic[T]):
    name: str = ""
    version: str = "1.0.0"
    description: str = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.name:
            cls.name = cls.__name__

    @abc.abstractmethod
    async def run(self, ctx: AgentContext) -> AgentResult[T]:
        """Execute the agent's responsibility against the encounter context."""
        raise NotImplementedError

    # Hook points subclasses can override -----------------------------------

    def input_summary(self, ctx: AgentContext) -> dict[str, Any]:
        """Compact, JSON-safe summary of what this agent received as input."""
        return {"encounter_id": ctx.encounter_id, "actor": ctx.actor}

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Agent {self.name} v{self.version}>"
