"""Agent-run inspection endpoints (per-encounter and registry list)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories import AgentRunRepository, EncounterRepository
from app.routers._dependencies import get_orchestrator
from app.schemas.pipeline import AgentRunOut


router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("")
def list_registered_agents(orchestrator = Depends(get_orchestrator)):
    return {
        "agents": [
            {
                "name":        a.name,
                "version":     a.version,
                "description": a.description,
            }
            for a in orchestrator.registry.all()
        ],
    }


@router.get("/runs/{encounter_id}", response_model=list[AgentRunOut])
def list_runs_for_encounter(encounter_id: str, db: Session = Depends(get_db)):
    EncounterRepository(db).get_or_404(encounter_id)
    runs = AgentRunRepository(db).for_encounter(encounter_id)
    return [AgentRunOut.model_validate(r) for r in runs]
