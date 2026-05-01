"""Agent-layer exceptions."""


class AgentError(Exception):
    """Base class for all agent failures."""
    retriable: bool = False


class AgentValidationError(AgentError):
    """The agent's input or precondition was invalid — never retry."""
    retriable = False


class AgentExecutionError(AgentError):
    """A transient execution failure (network, model, IO) — safe to retry."""
    retriable = True
