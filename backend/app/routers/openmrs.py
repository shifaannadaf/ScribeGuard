"""
Legacy OpenMRS router — preserves the OpenMRS FHIR R4 admin endpoints from
the previous codebase (`/openmrs/...`). The new agentic submission flow lives
under /encounters/{id}/submit (see app/routers/submissions.py).
"""
from app.openmrs.router import router  # noqa: F401
