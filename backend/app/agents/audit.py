"""
Agent 7 — Audit & Traceability Agent.

While every other agent emits its own audit events through the AuditRepository,
this agent owns the *meta* concerns:

    - On demand, build a complete chronological audit trail for an encounter.
    - Compute per-encounter traceability summaries (counts, durations,
      who-did-what timestamps, retry totals).
    - Provide a single place we can extend with future compliance / export
      hooks (e.g. SIEM forwarding, immutable log shipping) without changing
      every other agent.

The agent is invoked by the audit/observability routes; it never blocks
the main encounter pipeline.
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents import Agent, AgentContext, AgentResult


logger = logging.getLogger("scribeguard.agents.audit")


class AuditTraceabilityAgent(Agent[dict[str, Any]]):
    name = "AuditTraceabilityAgent"
    version = "1.0.0"
    description = (
        "Aggregates the agent-run + audit-event streams into a single, "
        "ordered traceability report for the encounter."
    )

    def input_summary(self, ctx: AgentContext) -> dict[str, Any]:
        return {"encounter_id": ctx.encounter_id, "actor": ctx.actor}

    async def run(self, ctx: AgentContext) -> AgentResult[dict[str, Any]]:
        events = ctx.audit.for_encounter(ctx.encounter_id)
        runs   = ctx.agent_runs.for_encounter(ctx.encounter_id)

        timeline = sorted(
            [
                {
                    "kind":       "audit",
                    "ts":         e.created_at.isoformat(),
                    "agent":      e.agent_name,
                    "event_type": e.event_type,
                    "severity":   e.severity,
                    "actor":      e.actor,
                    "summary":    e.summary,
                    "payload":    e.payload,
                }
                for e in events
            ] + [
                {
                    "kind":       "agent_run",
                    "ts":         r.started_at.isoformat(),
                    "agent":      r.agent_name,
                    "agent_version": r.agent_version,
                    "status":     r.status.value if hasattr(r.status, "value") else str(r.status),
                    "attempt":    r.attempt,
                    "duration_ms": r.duration_ms,
                    "error":      r.error_message,
                }
                for r in runs
            ],
            key=lambda x: x["ts"],
        )

        # Per-agent rollup
        agg: dict[str, dict[str, Any]] = {}
        for r in runs:
            a = agg.setdefault(r.agent_name, {"runs": 0, "succeeded": 0, "failed": 0, "total_ms": 0.0})
            a["runs"] += 1
            if r.status.value == "succeeded":
                a["succeeded"] += 1
            elif r.status.value == "failed":
                a["failed"] += 1
            if r.duration_ms:
                a["total_ms"] += float(r.duration_ms)

        return AgentResult(
            success=True,
            output={
                "events_count":  len(events),
                "runs_count":    len(runs),
                "timeline":      timeline,
                "rollup":        agg,
            },
            summary={
                "events_count": len(events),
                "runs_count":   len(runs),
                "agents":       sorted(agg.keys()),
            },
        )
