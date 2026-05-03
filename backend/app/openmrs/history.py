"""
Read patient history from OpenMRS for AI Assistant context.

Endpoints used:
    GET /Condition?patient={uuid}          → patient conditions/diagnoses
    GET /MedicationDispense?patient={uuid} → patient medications
    GET /AllergyIntolerance?patient={uuid} → patient allergies
    GET /Observation?patient={uuid}        → patient vital signs
    GET /Immunization?patient={uuid}       → patient immunizations
    GET /Encounter?patient={uuid}          → patient encounters
"""

import logging
from typing import Any
from datetime import datetime

from .client import fhir_get

logger = logging.getLogger(__name__)


def _format_date(date_str: str | None) -> str:
    """Format ISO date string to readable format."""
    if not date_str:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d")
    except:
        return date_str


def get_patient_history(patient_uuid: str) -> dict[str, Any]:
    """
    Fetch complete patient history from OpenMRS.
    
    Returns a dictionary with:
        - conditions: list of diagnoses
        - medications: list of active medications
        - allergies: list of known allergies
        - vitals: recent vital signs
        - immunizations: vaccination history
        - encounters: recent encounters
    """
    logger.info(f"Fetching patient history for {patient_uuid}")
    
    history = {
        "conditions": [],
        "medications": [],
        "allergies": [],
        "vitals": [],
        "immunizations": [],
        "encounters": []
    }
    
    try:
        # Get conditions/diagnoses
        conditions_bundle = fhir_get("Condition", params={"patient": patient_uuid})
        for entry in conditions_bundle.get("entry", []):
            resource = entry.get("resource", {})
            code = resource.get("code", {})
            condition_name = code.get("text", "Unknown condition")
            onset = _format_date(resource.get("onsetDateTime"))
            status = resource.get("clinicalStatus", {}).get("text", "Unknown")
            
            history["conditions"].append({
                "name": condition_name,
                "onset": onset,
                "status": status
            })
        
        logger.info(f"Found {len(history['conditions'])} conditions")
    except Exception as e:
        logger.warning(f"Failed to fetch conditions: {e}")
    
    try:
        # Get medications
        meds_bundle = fhir_get("MedicationDispense", params={"patient": patient_uuid})
        for entry in meds_bundle.get("entry", []):
            resource = entry.get("resource", {})
            med_concept = resource.get("medicationCodeableConcept", {})
            med_name = med_concept.get("text", "Unknown medication")
            dosage = resource.get("dosageInstruction", [{}])[0].get("text", "")
            
            history["medications"].append({
                "name": med_name,
                "dosage": dosage
            })
        
        logger.info(f"Found {len(history['medications'])} medications")
    except Exception as e:
        logger.warning(f"Failed to fetch medications: {e}")
    
    try:
        # Get allergies
        allergies_bundle = fhir_get("AllergyIntolerance", params={"patient": patient_uuid})
        for entry in allergies_bundle.get("entry", []):
            resource = entry.get("resource", {})
            code = resource.get("code", {})
            allergen = code.get("text", "Unknown allergen")
            reaction_list = resource.get("reaction", [])
            reaction = reaction_list[0].get("manifestation", [{}])[0].get("text", "") if reaction_list else ""
            severity = resource.get("criticality", "unknown")
            
            history["allergies"].append({
                "allergen": allergen,
                "reaction": reaction,
                "severity": severity
            })
        
        logger.info(f"Found {len(history['allergies'])} allergies")
    except Exception as e:
        logger.warning(f"Failed to fetch allergies: {e}")
    
    try:
        # Get recent vitals (observations)
        obs_bundle = fhir_get("Observation", params={
            "patient": patient_uuid,
            "_sort": "-date",
            "_count": "10"
        })
        for entry in obs_bundle.get("entry", []):
            resource = entry.get("resource", {})
            code = resource.get("code", {})
            obs_name = code.get("text", "Unknown observation")
            value_qty = resource.get("valueQuantity", {})
            value = value_qty.get("value")
            unit = value_qty.get("unit", "")
            date = _format_date(resource.get("effectiveDateTime"))
            
            if value:
                history["vitals"].append({
                    "name": obs_name,
                    "value": f"{value} {unit}".strip(),
                    "date": date
                })
        
        logger.info(f"Found {len(history['vitals'])} vital observations")
    except Exception as e:
        logger.warning(f"Failed to fetch vitals: {e}")
    
    try:
        # Get immunizations
        imm_bundle = fhir_get("Immunization", params={"patient": patient_uuid})
        for entry in imm_bundle.get("entry", []):
            resource = entry.get("resource", {})
            vaccine_code = resource.get("vaccineCode", {})
            vaccine_name = vaccine_code.get("text", "Unknown vaccine")
            date = _format_date(resource.get("occurrenceDateTime"))
            
            history["immunizations"].append({
                "vaccine": vaccine_name,
                "date": date
            })
        
        logger.info(f"Found {len(history['immunizations'])} immunizations")
    except Exception as e:
        logger.warning(f"Failed to fetch immunizations: {e}")
    
    try:
        # Get recent encounters
        enc_bundle = fhir_get("Encounter", params={
            "patient": patient_uuid,
            "_sort": "-date",
            "_count": "5"
        })
        for entry in enc_bundle.get("entry", []):
            resource = entry.get("resource", {})
            type_list = resource.get("type", [])
            enc_type = type_list[0].get("text", "Unknown") if type_list else "Unknown"
            date = _format_date(resource.get("period", {}).get("start"))
            status = resource.get("status", "unknown")
            
            history["encounters"].append({
                "type": enc_type,
                "date": date,
                "status": status
            })
        
        logger.info(f"Found {len(history['encounters'])} encounters")
    except Exception as e:
        logger.warning(f"Failed to fetch encounters: {e}")
    
    return history


def format_history_for_prompt(history: dict[str, Any]) -> str:
    """
    Format patient history into a readable string for GPT prompt.
    """
    sections = []
    
    if history["conditions"]:
        cond_lines = [f"- {c['name']} (onset: {c['onset']}, status: {c['status']})" 
                     for c in history["conditions"]]
        sections.append("DIAGNOSES/CONDITIONS:\n" + "\n".join(cond_lines))
    
    if history["medications"]:
        med_lines = [f"- {m['name']}" + (f" - {m['dosage']}" if m['dosage'] else "")
                    for m in history["medications"]]
        sections.append("CURRENT MEDICATIONS:\n" + "\n".join(med_lines))
    
    if history["allergies"]:
        allergy_lines = [f"- {a['allergen']} ({a['severity']})" + 
                        (f" - {a['reaction']}" if a['reaction'] else "")
                        for a in history["allergies"]]
        sections.append("KNOWN ALLERGIES:\n" + "\n".join(allergy_lines))
    
    if history["vitals"]:
        vital_lines = [f"- {v['name']}: {v['value']} ({v['date']})" 
                      for v in history["vitals"][:5]]  # Show only 5 most recent
        sections.append("RECENT VITALS:\n" + "\n".join(vital_lines))
    
    if history["immunizations"]:
        imm_lines = [f"- {i['vaccine']} on {i['date']}" 
                    for i in history["immunizations"]]
        sections.append("IMMUNIZATION HISTORY:\n" + "\n".join(imm_lines))
    
    if history["encounters"]:
        enc_lines = [f"- {e['type']} on {e['date']} ({e['status']})" 
                    for e in history["encounters"]]
        sections.append("RECENT ENCOUNTERS:\n" + "\n".join(enc_lines))
    
    if not sections:
        return "No patient history available in OpenMRS."
    
    return "\n\n".join(sections)
