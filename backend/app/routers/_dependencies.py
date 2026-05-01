"""Shared FastAPI dependencies (orchestrator factory + auth stub)."""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.orchestrator import AgentOrchestrator, build_default_registry


@lru_cache(maxsize=1)
def _registry():
    return build_default_registry()


def get_orchestrator(db: Session = Depends(get_db)) -> AgentOrchestrator:
    return AgentOrchestrator(db=db, registry=_registry())
