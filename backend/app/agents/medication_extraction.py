"""
Backward-compatibility shim.

The previous medication-only extractor has been superseded by the
ClinicalEntityExtractionAgent which classifies medications, allergies,
conditions, vital signs, and follow-ups in a single pass. This module
re-exports the new agent under the legacy name so any external imports
keep working.
"""
from app.agents.clinical_extraction import ClinicalEntityExtractionAgent as MedicationExtractionAgent  # noqa: F401

__all__ = ["MedicationExtractionAgent"]
