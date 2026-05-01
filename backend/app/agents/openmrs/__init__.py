"""
OpenMRS integration agents.

`OpenMRSIntegrationAgent` is the public-facing system-of-record boundary.
Internally it delegates to focused sub-agents so each step
(authenticate, fetch context, map, write, verify) is independently
testable and observable.
"""
from app.agents.openmrs.integration import OpenMRSIntegrationAgent

__all__ = ["OpenMRSIntegrationAgent"]
