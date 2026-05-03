"""
FHIR R4 Condition resource operations.

Endpoints used:
    GET    /Condition?patient={uuid}   → list conditions for a patient
    POST   /Condition                  → create a new condition/diagnosis
    PATCH  /Condition/{uuid}           → partial update (JSON Patch)
    DELETE /Condition/{uuid}           → delete a condition
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .client import fhir_get, fhir_post, fhir_patch, fhir_delete, rest_get, rest_post

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _rest_date(date_str: str) -> str:
    """Convert YYYY-MM-DD to REST API format: YYYY-MM-DDTHH:MM:SS.000+0000"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%dT00:00:00.000+0000")
    except Exception:
        return date_str


def search_concept(query: str) -> Optional[str]:
    """
    Search for a concept in OpenMRS by name and return the UUID.
    Tries multiple search strategies and validates results match the query.
    Returns None if no match found.
    """
    import re
    from difflib import SequenceMatcher
    
    def similarity(a: str, b: str) -> float:
        """Calculate string similarity (0-1)."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def is_good_match(concept_name: str, query: str) -> bool:
        """Check if concept name is a reasonable match for the query."""
        concept_lower = concept_name.lower()
        query_lower = query.lower()
        
        # Check if main keywords from query appear in concept name
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        concept_words = set(re.findall(r'\b\w+\b', concept_lower))
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'of', 'with', 'to', 'in', 'on', 'at', 'associated'}
        query_words -= common_words
        concept_words -= common_words
        
        # Calculate overlap - at least 60% of query words should be in concept
        if query_words:
            overlap = len(query_words & concept_words) / len(query_words)
            return overlap >= 0.6 and similarity(concept_name, query) >= 0.5
        
        return similarity(concept_name, query) >= 0.6
    
    # Strategy 1: Try exact query first, get multiple results to find best match
    try:
        data = rest_get("concept", params={"q": query, "limit": 5})
        results = data.get("results", [])
        
        # Find best matching result
        best_match = None
        best_score = 0
        
        for result in results:
            concept_name = result.get("display", "")
            score = similarity(concept_name, query)
            
            # Prefer exact or very close matches
            if concept_name.lower() == query.lower():
                concept_uuid = result.get("uuid")
                logger.info("Found exact concept match: %s → %s", concept_name, concept_uuid)
                return concept_uuid
            
            if is_good_match(concept_name, query) and score > best_score:
                best_match = result
                best_score = score
        
        if best_match and best_score >= 0.5:
            concept_uuid = best_match.get("uuid")
            concept_name = best_match.get("display")
            logger.info("Found concept: %s → %s (match score: %.2f)", concept_name, concept_uuid, best_score)
            return concept_uuid
            
    except Exception as e:
        logger.warning("Failed to search concept '%s': %s", query, e)
    
    # Strategy 2: Try without parenthetical parts (e.g., "Essential (primary) hypertension" → "Essential hypertension")
    simplified_query = re.sub(r'\s*\([^)]*\)\s*', ' ', query).strip()
    if simplified_query != query:
        try:
            data = rest_get("concept", params={"q": simplified_query, "limit": 5})
            results = data.get("results", [])
            
            for result in results:
                concept_name = result.get("display", "")
                if is_good_match(concept_name, simplified_query):
                    concept_uuid = result.get("uuid")
                    logger.info("Found concept: %s → %s (simplified: %s)", concept_name, concept_uuid, simplified_query)
                    return concept_uuid
        except Exception as e:
            logger.warning("Failed to search simplified concept '%s': %s", simplified_query, e)
    
    # Strategy 3: Try just the main word(s) - last word for most conditions
    words = query.split()
    if len(words) > 1:
        last_word = words[-1]
        try:
            data = rest_get("concept", params={"q": last_word, "limit": 5})
            results = data.get("results", [])
            
            for result in results:
                concept_name = result.get("display", "")
                # For keyword search, require decent similarity to avoid wrong matches
                if similarity(concept_name, query) >= 0.4:
                    concept_uuid = result.get("uuid")
                    logger.info("Found concept: %s → %s (keyword: %s)", concept_name, concept_uuid, last_word)
                    return concept_uuid
        except Exception as e:
            logger.warning("Failed to search keyword '%s': %s", last_word, e)
    
    logger.error("No concept found for '%s' after trying all strategies", query)
    return None


def create_condition_rest(
    patient_uuid: str,
    condition_name: str,
    onset_date: Optional[str] = None,
    clinical_status: str = "ACTIVE",
    verification_status: str = "CONFIRMED"
) -> dict:
    """
    Create a condition using OpenMRS REST API (not FHIR).
    This approach properly displays condition names in OpenMRS UI.
    
    Args:
        patient_uuid: Patient UUID
        condition_name: Human-readable condition name (e.g., "Constipation")
        onset_date: Date string "YYYY-MM-DD" (optional)
        clinical_status: "ACTIVE" or "INACTIVE"
        verification_status: "CONFIRMED", "PROVISIONAL", etc.
    
    Returns the created condition resource.
    """
    # Search for concept UUID by name
    concept_uuid = search_concept(condition_name)
    if not concept_uuid:
        logger.error("Cannot create condition: concept not found for '%s'", condition_name)
        raise ValueError(f"Concept not found: {condition_name}")
    
    payload = {
        "patient": patient_uuid,
        "condition": {"coded": concept_uuid},
        "clinicalStatus": clinical_status,
        "verificationStatus": verification_status,
    }
    
    if onset_date:
        payload["onsetDate"] = _rest_date(onset_date)
    
    data = rest_post("condition", payload)
    logger.info("Created Condition (REST) UUID=%s for patient %s: %s", 
                data.get("uuid"), patient_uuid, condition_name)
    return data


def get_conditions(patient_uuid: str) -> dict:
    """
    READ — List all conditions/diagnoses for a patient.

    GET /Condition?patient={uuid}

    Returns a FHIR Bundle of Condition resources.

    Example:
        conditions = get_conditions("076154fc-381d-4805-a5b9-13b90f667717")
    """
    data = fhir_get("Condition", params={"patient": patient_uuid})
    logger.info("Fetched %d condition(s) for patient %s",
                data.get("total", 0), patient_uuid)
    return data


def create_condition(
    patient_uuid: str,
    icd10_code: str = "E14.9",
    snomed_code: Optional[str] = None,
    display: str = "Diabetes mellitus",
    recorded_date: str = "2025-10-02",
    onset_datetime: Optional[str] = None,
) -> dict:
    """
    CREATE — Record a new condition/diagnosis for a patient.

    POST /Condition

    Uses ICD-10-CM coding (SNOMED CT is optional).

    Args:
        patient_uuid:    Patient UUID
        icd10_code:      ICD-10-CM code (e.g. "E14.9")
        snomed_code:     SNOMED CT code  (e.g. "73211009") - optional
        display:         Human-readable condition name
        recorded_date:   Date string "YYYY-MM-DD"
        onset_datetime:  ISO datetime string (defaults to now)

    Returns the created Condition resource with its UUID at ["id"].

    Example:
        cond = create_condition(
            patient_uuid="076154fc-...",
            icd10_code="J06.9",
            snomed_code="54150009",
            display="Upper respiratory infection",
        )
        condition_uuid = cond["id"]
    """
    onset_datetime = onset_datetime or _now_iso()

    # Search for OpenMRS concept UUID
    concept_uuid = search_concept(display)

    payload = {
        "resourceType": "Condition",
        "clinicalStatus": {
            "coding": [{
                "system":  "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code":    "active",
                "display": "Active",
            }],
            "text": "Active",
        },
        "verificationStatus": {
            "coding": [{
                "system":  "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code":    "confirmed",
                "display": "Confirmed",
            }],
            "text": "Confirmed",
        },
        "category": [{
            "coding": [{
                "system":  "http://terminology.hl7.org/CodeSystem/condition-category",
                "code":    "problem-list-item",
                "display": "Problem List Item",
            }],
            "text": "Problem List Item",
        }],
        "code": {
            "coding": [],
            "text": display,
        },
        "subject":         {"reference": f"Patient/{patient_uuid}"},
        "recordedDate":    recorded_date,
        "onsetDateTime":   onset_datetime,
    }

    # Add OpenMRS concept reference if found
    if concept_uuid:
        payload["code"]["coding"].append({
            "code": concept_uuid,
            "display": display
        })
    
    # Add ICD-10 code as additional coding
    payload["code"]["coding"].append({
        "system": "http://hl7.org/fhir/sid/icd-10-cm",
        "code": icd10_code,
        "display": display
    })

    # Add SNOMED code only if provided
    if snomed_code:
        payload["code"]["coding"].append({
            "system": "http://snomed.info/sct",
            "code": snomed_code,
            "display": display
        })

    data = fhir_post("Condition", payload)
    logger.info("Created Condition UUID=%s for patient %s", data.get("id"), patient_uuid)
    return data


def update_condition(condition_uuid: str, json_patch: list[dict]) -> dict:
    """
    UPDATE — Partial update using JSON Patch (RFC 6902).

    PATCH /Condition/{uuid}
    Content-Type: application/json-patch+json

    Args:
        condition_uuid: UUID of the Condition to update
        json_patch:     List of RFC 6902 patch operations

    Common patch examples:
        # Mark condition as inactive (resolved)
        [{"op": "replace", "path": "/clinicalStatus/coding/0/code", "value": "inactive"}]

        # Mark as resolved
        [{"op": "replace", "path": "/clinicalStatus/coding/0/code", "value": "resolved"}]

    Example:
        updated = update_condition(
            "87f5a1f2-...",
            [{"op": "replace", "path": "/clinicalStatus/coding/0/code", "value": "inactive"}]
        )
    """
    data = fhir_patch(f"Condition/{condition_uuid}", json_patch)
    logger.info("Updated Condition %s", condition_uuid)
    return data


def delete_condition(condition_uuid: str) -> bool:
    """
    DELETE — Remove a condition record.

    DELETE /Condition/{uuid}

    Returns True on success.

    Example:
        delete_condition("87f5a1f2-1f73-4d67-9969-d096940606d3")
    """
    fhir_delete(f"Condition/{condition_uuid}")
    logger.info("Deleted Condition %s", condition_uuid)
    return True