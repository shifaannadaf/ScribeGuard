"""
ScribeGuard FastAPI bootstrap.

The agent orchestrator is wired in here as a single shared registry of agent
instances. Routers obtain the orchestrator on each request via dependency
injection so each request sees its own DB session.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    encounters,
    pipeline,
    physician_review,
    soap,
    medications,
    submissions,
    agents as agents_router,
    audit as audit_router,
    openmrs as openmrs_router,
    patient_context as patient_context_router,
    chat,
    export,
)


# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)


app = FastAPI(
    title="ScribeGuard Agentic API",
    description=(
        "ScribeGuard is an agentic AI clinical documentation platform. "
        "Specialized autonomous agents (Intake, Transcription, SOAP "
        "Generation, Medication Extraction, Physician Review, OpenMRS "
        "Integration, Audit) collaborate to convert recorded encounters "
        "into structured, physician-approved clinical notes that are "
        "written back to OpenMRS."
    ),
    version="2.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers ─────────────────────────────────────────────────────────────────
app.include_router(encounters.router)
app.include_router(pipeline.router)
app.include_router(physician_review.router)
app.include_router(soap.router)
app.include_router(medications.router)
app.include_router(submissions.router)
app.include_router(agents_router.router)
app.include_router(audit_router.router)
app.include_router(patient_context_router.router)
app.include_router(openmrs_router.router)
app.include_router(chat.router)
app.include_router(export.router)


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "version": app.version,
        "openmrs_simulated": settings.OPENMRS_SIMULATE,
    }


@app.get("/", tags=["Health"])
def root():
    return {
        "name": "ScribeGuard Agentic API",
        "version": app.version,
        "docs": "/docs",
    }
