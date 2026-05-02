from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
import httpx

from app.db.database import get_db
from app.models.models import Encounter, AuditLog, EncounterStatus
from app.schemas.misc import OpenMRSPatient, PushRequest, PushResponse

# Import FHIR modules
from app.openmrs import encounter as omrs_encounter
from app.openmrs import observation as omrs_obs
from app.openmrs import condition as omrs_condition
from app.openmrs import medication as omrs_med
from app.openmrs import allergy as omrs_allergy
from app.openmrs import patient as omrs_patient
from app.openmrs.config import DEFAULT_PRACTITIONER_UUID, DEFAULT_LOCATION_UUID

router = APIRouter(tags=["OpenMRS"])
logger = logging.getLogger(__name__)


@router.get("/openmrs/patients/{patient_id}", response_model=OpenMRSPatient)
def get_openmrs_patient(patient_id: str):
    # Stub — real OpenMRS GET goes here
    return OpenMRSPatient(
        uuid="openmrs-mock-uuid-001",
        name="John Doe",
        identifier=patient_id,
        birthdate="1985-06-12",
        gender="M",
        active_medications=[],
        known_allergies=[],
    )


@router.post("/encounters/{encounter_id}/push", response_model=PushResponse)
def push_to_openmrs(encounter_id: str, body: PushRequest, db: Session = Depends(get_db)):
    """
    Push approved encounter data to OpenMRS via FHIR:
    - Create new patient if needed (when openmrs_patient_uuid is None)
    - Create Encounter resource
    - Push vitals as Observations
    - Push diagnoses as Conditions
    - Push medications as MedicationDispense
    - Push allergies as AllergyIntolerance
    - Push immunizations as Immunization
    """
    enc = db.get(Encounter, encounter_id)
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if enc.status != EncounterStatus.approved:
        raise HTTPException(status_code=400, detail="Encounter must be approved before pushing")
    if enc.status == EncounterStatus.pushed:
        raise HTTPException(status_code=400, detail="Encounter has already been pushed to OpenMRS")
    
    openmrs_patient_uuid = body.openmrs_patient_uuid

    pushed_resources = {
        "patient_uuid": None,
        "patient_created": False,
        "encounter_uuid": None,
        "vitals": [],
        "conditions": [],
        "medications": [],
        "allergies": [],
    }

    try:
        # 1. Create patient in OpenMRS if needed (for new patients)
        if not openmrs_patient_uuid:
            logger.info(f"Creating new patient in OpenMRS: {enc.patient_name}")
            # Parse patient name
            name_parts = enc.patient_name.strip().split(" ", 1)
            given_name = name_parts[0]
            family_name = name_parts[1] if len(name_parts) > 1 else ""
            
            patient_resource = omrs_patient.create_patient(
                given_name=given_name,
                family_name=family_name,
                identifier=enc.patient_id,
                gender="unknown",  # Gender not captured in encounter
            )
            openmrs_patient_uuid = patient_resource.get("id")
            pushed_resources["patient_uuid"] = openmrs_patient_uuid
            pushed_resources["patient_created"] = True
            logger.info(f"Created patient in OpenMRS: {openmrs_patient_uuid}")
        else:
            pushed_resources["patient_uuid"] = openmrs_patient_uuid
            logger.info(f"Using existing patient: {openmrs_patient_uuid}")

        # 2. Create Encounter in OpenMRS
        logger.info(f"Creating encounter in OpenMRS for patient {openmrs_patient_uuid}")
        logger.info(f"Using practitioner: {DEFAULT_PRACTITIONER_UUID}, location: {DEFAULT_LOCATION_UUID}")
        encounter_resource = omrs_encounter.create_encounter(
            patient_ref=f"Patient/{openmrs_patient_uuid}",
            practitioner_ref=f"Practitioner/{DEFAULT_PRACTITIONER_UUID}",
            location_ref=f"Location/{DEFAULT_LOCATION_UUID}",
        )
        encounter_uuid = encounter_resource.get("id")
        pushed_resources["encounter_uuid"] = encounter_uuid
        logger.info(f"Created Encounter {encounter_uuid}")

        # 3. Push Vitals as Observations
        if enc.vitals:
            logger.info("Pushing vitals to OpenMRS...")
            vitals = enc.vitals
            
            if vitals.get("height_cm"):
                obs = omrs_obs.create_obs_height(openmrs_patient_uuid, float(vitals["height_cm"]))
                pushed_resources["vitals"].append(obs.get("id"))
                logger.info(f"Pushed height observation")
            
            if vitals.get("weight_kg"):
                obs = omrs_obs.create_obs_weight(openmrs_patient_uuid, float(vitals["weight_kg"]))
                pushed_resources["vitals"].append(obs.get("id"))
                logger.info(f"Pushed weight observation")
            
            if vitals.get("temperature_c"):
                obs = omrs_obs.create_obs_temperature(openmrs_patient_uuid, float(vitals["temperature_c"]))
                pushed_resources["vitals"].append(obs.get("id"))
                logger.info(f"Pushed temperature observation")
            
            if vitals.get("resp_rate"):
                obs = omrs_obs.create_obs_respiratory_rate(openmrs_patient_uuid, float(vitals["resp_rate"]))
                pushed_resources["vitals"].append(obs.get("id"))
                logger.info(f"Pushed respiratory rate observation")
            
            if vitals.get("spo2_pct"):
                obs = omrs_obs.create_obs_spo2(openmrs_patient_uuid, float(vitals["spo2_pct"]))
                pushed_resources["vitals"].append(obs.get("id"))
                logger.info(f"Pushed SpO2 observation")
            
            # Note: BP systolic/diastolic and pulse not yet implemented in observation.py

        # 4. Push Diagnoses as Conditions (using REST API for proper display)
        if enc.diagnoses:
            logger.info(f"Pushing {len(enc.diagnoses)} diagnoses to OpenMRS...")
            
            # First, get existing conditions to avoid duplicates
            try:
                from difflib import SequenceMatcher
                
                def is_similar(a: str, b: str, threshold: float = 0.7) -> bool:
                    """Check if two condition names are similar enough to be considered duplicates."""
                    import re
                    
                    # Normalize: lowercase, remove punctuation, sort words
                    def normalize(text: str) -> set:
                        words = re.findall(r'\b\w+\b', text.lower())
                        # Remove common filler words
                        stop_words = {'the', 'a', 'an', 'of', 'with', 'to', 'in', 'on', 'at', 'type', 'associated'}
                        return set(w for w in words if w not in stop_words)
                    
                    words_a = normalize(a)
                    words_b = normalize(b)
                    
                    if not words_a or not words_b:
                        return False
                    
                    # Calculate word overlap
                    overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
                    
                    # Also check string similarity
                    similarity = SequenceMatcher(None, a.lower(), b.lower()).ratio()
                    
                    # Consider duplicate if high overlap OR high similarity
                    return overlap >= threshold or similarity >= threshold
                
                existing_conditions_bundle = omrs_condition.get_conditions(openmrs_patient_uuid)
                existing_condition_names = []
                for entry in existing_conditions_bundle.get("entry", []):
                    resource = entry.get("resource", {})
                    code = resource.get("code", {})
                    text = code.get("text", "")
                    if text:
                        existing_condition_names.append(text)
                logger.info(f"Found {len(existing_condition_names)} existing conditions for patient")
            except Exception as e:
                logger.warning(f"Could not fetch existing conditions: {e}")
                existing_condition_names = []
            
            for dx in enc.diagnoses:
                # Check if similar condition already exists
                is_duplicate = False
                for existing_name in existing_condition_names:
                    if is_similar(dx.description, existing_name):
                        logger.info(f"Skipping duplicate condition: '{dx.description}' (similar to existing '{existing_name}')")
                        is_duplicate = True
                        break
                
                if is_duplicate:
                    continue
                
                logger.info(f"Creating condition: {dx.description}")
                try:
                    condition = omrs_condition.create_condition_rest(
                        patient_uuid=openmrs_patient_uuid,
                        condition_name=dx.description,
                        onset_date=None,  # Can add onset_date if available
                        clinical_status="ACTIVE",
                        verification_status="CONFIRMED",
                    )
                    condition_uuid = condition.get("uuid")
                    pushed_resources["conditions"].append(condition_uuid)
                    logger.info(f"Pushed condition {dx.description} ({condition_uuid})")
                except ValueError as e:
                    logger.warning(f"Skipping condition '{dx.description}': {e}")
                except Exception as e:
                    logger.warning(f"Failed to push condition '{dx.description}': {e}")

        # 5. Push Active + Past Medications via REST drug orders
        all_meds = list(enc.medications or []) + list(enc.past_medications or [])
        if all_meds:
            logger.info(f"Pushing {len(all_meds)} medications to OpenMRS...")
            try:
                _, med_encounter_uuid = omrs_med.create_medication_visit(openmrs_patient_uuid)
                for med in all_meds:
                    try:
                        order = omrs_med.create_drug_order(
                            patient_uuid=openmrs_patient_uuid,
                            encounter_uuid=med_encounter_uuid,
                            medication_name=med.name,
                            dose=med.dose or "",
                            route=med.route or "",
                            frequency=med.frequency or "",
                        )
                        pushed_resources["medications"].append(order.get("uuid"))
                        logger.info(f"Pushed medication: {med.name}")
                    except Exception as e:
                        logger.warning(f"Failed to push medication '{med.name}': {e}")
            except Exception as e:
                logger.warning(f"Failed to create medication visit/encounter: {e}")

        # 6. Push Allergies as AllergyIntolerance
        if enc.allergies:
            logger.info(f"Pushing {len(enc.allergies)} allergies to OpenMRS...")
            
            # First, get existing allergies to avoid duplicates
            try:
                existing_allergies_bundle = omrs_allergy.get_allergies(openmrs_patient_uuid)
                existing_allergens = set()
                for entry in existing_allergies_bundle.get("entry", []):
                    resource = entry.get("resource", {})
                    code = resource.get("code", {})
                    text = code.get("text", "").lower()
                    existing_allergens.add(text)
                logger.info(f"Found {len(existing_allergens)} existing allergies for patient")
            except Exception as e:
                logger.warning(f"Could not fetch existing allergies: {e}")
                existing_allergens = set()
            
            for allergy in enc.allergies:
                allergen_lower = allergy.allergen.lower()
                
                # Skip if allergy already exists
                if allergen_lower in existing_allergens:
                    logger.info(f"Skipping duplicate allergy: {allergy.allergen}")
                    continue
                
                try:
                    severity_map = {"Mild": "mild", "Moderate": "moderate", "Severe": "severe"}
                    severity = severity_map.get(allergy.severity or "", "moderate")
                    
                    allergy_resource = omrs_allergy.create_allergy(
                        patient_uuid=openmrs_patient_uuid,
                        substance_display=allergy.allergen,
                        manifestation_display=allergy.reaction or "Allergic reaction",
                        severity=severity,
                    )
                    allergy_uuid = allergy_resource.get("id")
                    pushed_resources["allergies"].append(allergy_uuid)
                    logger.info(f"Pushed allergy {allergy.allergen} ({allergy_uuid})")
                except httpx.HTTPStatusError as e:
                    if "duplicateAllergen" in e.response.text:
                        logger.info(f"Allergy '{allergy.allergen}' already exists in OpenMRS, skipping")
                    else:
                        logger.warning(f"Failed to push allergy '{allergy.allergen}': {e.response.text}")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to push allergy '{allergy.allergen}': {e}")
                    continue

        # Update encounter status to pushed
        enc.status = EncounterStatus.pushed
        enc.openmrs_uuid = encounter_uuid
        enc.updated_at = datetime.now(timezone.utc)
        db.add(AuditLog(
            encounter_id=enc.id,
            action="pushed",
            actor="guest",
            detail={
                "openmrs_patient_uuid": openmrs_patient_uuid,
                "pushed_resources": pushed_resources,
            }
        ))
        db.commit()

        logger.info(f"Successfully pushed encounter {encounter_id} to OpenMRS")
        return PushResponse(
            id=enc.id,
            status="pushed",
            openmrs_uuid=enc.openmrs_uuid,
            pushed_at=enc.updated_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to push encounter {encounter_id} to OpenMRS: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to push to OpenMRS: {str(e)}"
        )
