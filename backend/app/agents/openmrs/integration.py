"""
Agent 6 — OpenMRS Integration Agent (composite).

End-to-end system-of-record write-back. Each step is recorded in
`submission_records` + emits an audit event so the entire flow is
observable.

Flow:
    1. OpenMRSAuthAgent              -- handshake / credential check
    2. OpenMRSPatientContextAgent    -- resolve Patient resource + chart snapshot
    3. OpenMRSEncounterMapperAgent   -- build FHIR payloads
    4. OpenMRSNoteWriterAgent        -- POST Encounter, Observation,
                                        Allergies, Conditions, Vitals,
                                        MedicationRequests
    5. OpenMRSSubmissionVerifierAgent -- read-back verification
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents import Agent, AgentContext, AgentResult
from app.agents.exceptions import AgentExecutionError, AgentValidationError
from app.agents.openmrs.auth import OpenMRSAuthAgent
from app.agents.openmrs.encounter_mapper import OpenMRSEncounterMapperAgent
from app.agents.openmrs.note_writer import OpenMRSNoteWriterAgent
from app.agents.openmrs.patient_context import OpenMRSPatientContextAgent
from app.agents.openmrs.verifier import OpenMRSSubmissionVerifierAgent
from app.config import settings
from app.models import EncounterStatus, ProcessingStage, SoapNoteStatus


logger = logging.getLogger("scribeguard.agents.openmrs.integration")


class OpenMRSIntegrationAgent(Agent[dict[str, Any]]):
    name = "OpenMRSIntegrationAgent"
    version = "1.2.0"
    description = (
        "Authenticates with OpenMRS, fetches patient context, maps the "
        "approved SOAP note + extracted entities into FHIR resources, "
        "writes them all, verifies them, and logs each attempt."
    )

    def __init__(self):
        self.auth     = OpenMRSAuthAgent()
        self.context  = OpenMRSPatientContextAgent()
        self.mapper   = OpenMRSEncounterMapperAgent()
        self.writer   = OpenMRSNoteWriterAgent()
        self.verifier = OpenMRSSubmissionVerifierAgent()

    def input_summary(self, ctx: AgentContext) -> dict[str, Any]:
        note = ctx.soap_notes.current_for(ctx.encounter_id)
        return {
            "encounter_id": ctx.encounter_id,
            "soap_note_id": note.id if note else None,
            "note_status":  note.status.value if note else None,
            "openmrs_patient_uuid": ctx.encounter.openmrs_patient_uuid,
            "simulate":     settings.OPENMRS_SIMULATE,
        }

    async def run(self, ctx: AgentContext) -> AgentResult[dict[str, Any]]:
        encounter = ctx.encounter
        note = ctx.soap_notes.current_for(ctx.encounter_id)

        if not note:
            raise AgentValidationError("No SOAP note to submit.")
        if note.status != SoapNoteStatus.approved:
            raise AgentValidationError(
                "SOAP note has not been approved by a physician — cannot submit."
            )
        if encounter.status != EncounterStatus.approved:
            raise AgentValidationError(
                "Encounter is not in 'approved' status — cannot submit."
            )

        ctx.encounters.set_processing_stage(encounter, ProcessingStage.submitting)
        record = ctx.submissions.create_pending(
            encounter_id=encounter.id,
            soap_note_id=note.id,
            openmrs_patient_uuid=ctx.payload.get("openmrs_patient_uuid")
                                or encounter.openmrs_patient_uuid,
        )

        try:
            # 1) Auth ────────────────────────────────────────────────
            auth_info = self.auth.authenticate()
            ctx.audit.append(
                encounter_id=encounter.id,
                event_type="openmrs.auth_ok",
                agent_name="OpenMRSAuthAgent",
                actor=ctx.actor,
                summary=f"Connected to {auth_info.get('server')} (FHIR {auth_info.get('fhirVersion')})",
                payload=auth_info,
            )

            # 2) Patient context (resolve + chart snapshot) ────────
            patient = self.context.resolve(
                openmrs_patient_uuid=record.openmrs_patient_uuid,
                local_patient_id=encounter.patient_id,
            )
            patient_uuid = patient["uuid"]
            if patient_uuid and not encounter.openmrs_patient_uuid:
                encounter.openmrs_patient_uuid = patient_uuid

            ctx.audit.append(
                encounter_id=encounter.id,
                event_type="openmrs.patient_resolved",
                agent_name="OpenMRSPatientContextAgent",
                actor=ctx.actor,
                summary=f"Resolved Patient/{patient_uuid}",
                payload={"uuid": patient_uuid, "name": patient.get("name")},
            )

            # 3) Map ────────────────────────────────────────────────
            practitioner_uuid = ctx.payload.get("practitioner_uuid") or self.mapper.default_practitioner_uuid()
            location_uuid     = ctx.payload.get("location_uuid")     or self.mapper.default_location_uuid()

            # Use the encounter's recorded date as the visit timestamp so all
            # resources (Encounter, Observations, Allergies, Conditions, Medications)
            # are filed under the correct visit date rather than the submission time.
            visit_ts = encounter.created_at.strftime("%Y-%m-%dT%H:%M:%S+00:00")

            encounter_payload = self.mapper.build_encounter_payload(
                patient_uuid=patient_uuid,
                practitioner_uuid=practitioner_uuid,
                location_uuid=location_uuid,
                when=visit_ts,
            )

            soap_md = self.mapper.soap_to_markdown(
                patient_name=encounter.patient_name,
                patient_id=encounter.patient_id,
                subjective=note.subjective,
                objective=note.objective,
                assessment=note.assessment,
                plan=note.plan,
            )

            ctx.submissions.mark_in_flight(record, {"patient": patient_uuid, "visit_ts": visit_ts})

            # 4a) Encounter (REST) ──────────────────────────────────
            try:
                openmrs_encounter_uuid = self.writer.create_encounter(
                    patient_uuid=patient_uuid,
                    visit_ts=visit_ts,
                    provider_uuid=practitioner_uuid,
                    location_uuid=location_uuid,
                )
            except Exception as exc:  # noqa: BLE001
                raise AgentExecutionError(f"OpenMRS Encounter write failed: {exc}") from exc

            # 4b) SOAP note Observation (REST) ────────────────────────
            try:
                openmrs_observation_uuid = self.writer.create_soap_observation(
                    patient_uuid=patient_uuid,
                    encounter_uuid=openmrs_encounter_uuid,
                    soap_text=soap_md,
                    obs_datetime=visit_ts,
                )
            except Exception as exc:  # noqa: BLE001
                raise AgentExecutionError(f"OpenMRS SOAP Observation write failed: {exc}") from exc

            # 4c) Vital signs (REST obs) ────────────────────────────
            vitals = ctx.entities.list_vital_signs(encounter.id)
            vital_uuids: list[str] = []
            vital_errors: list[str] = []
            for v in vitals:
                try:
                    obs_id = self.writer.create_vital(
                        patient_uuid=patient_uuid,
                        encounter_uuid=openmrs_encounter_uuid,
                        kind=v.kind,
                        value=v.value,
                        obs_datetime=visit_ts,
                    )
                    v.openmrs_resource_uuid = obs_id
                    if obs_id:
                        vital_uuids.append(obs_id)
                except Exception as exc:  # noqa: BLE001
                    vital_errors.append(f"{v.kind}: {exc}")

            # 4d) Allergies (REST) ──────────────────────────────────
            allergies = ctx.entities.list_allergies(encounter.id)
            allergy_uuids: list[str] = []
            allergy_errors: list[str] = []
            for a in allergies:
                try:
                    res_id = self.writer.create_allergy(
                        patient_uuid=patient_uuid,
                        substance=a.substance,
                        reaction=a.reaction,
                        severity=a.severity,
                        category=a.category,
                    )
                    a.openmrs_resource_uuid = res_id
                    if res_id:
                        allergy_uuids.append(res_id)
                except Exception as exc:  # noqa: BLE001
                    allergy_errors.append(f"{a.substance}: {exc}")

            # 4e) Conditions (REST) ─────────────────────────────────
            conditions = ctx.entities.list_conditions(encounter.id)
            condition_uuids: list[str] = []
            condition_errors: list[str] = []
            for c in conditions:
                try:
                    res_id = self.writer.create_condition(
                        patient_uuid=patient_uuid,
                        description=c.description,
                        icd10_code=c.icd10_code,
                        clinical_status=c.clinical_status,
                        onset_datetime=visit_ts,
                    )
                    c.openmrs_resource_uuid = res_id
                    if res_id:
                        condition_uuids.append(res_id)
                except Exception as exc:  # noqa: BLE001
                    condition_errors.append(f"{c.description}: {exc}")

            # 4f) Medications (REST drug orders) ────────────────────
            medications = ctx.medications.for_encounter(encounter.id)
            medication_uuids: list[str] = []
            medication_errors: list[str] = []
            for m in medications:
                try:
                    res_id = self.writer.create_medication_order(
                        patient_uuid=patient_uuid,
                        encounter_uuid=openmrs_encounter_uuid,
                        drug_name=m.name,
                        dose=m.dose,
                        route=m.route,
                        frequency=m.frequency,
                        duration=m.duration,
                    )
                    m.openmrs_resource_uuid = res_id
                    if res_id:
                        medication_uuids.append(res_id)
                except Exception as exc:  # noqa: BLE001
                    medication_errors.append(f"{m.name}: {exc}")

            # Persist submission outcome ─────────────────────────────
            response_summary = {
                "encounter_uuid":    openmrs_encounter_uuid,
                "observation_uuid":  openmrs_observation_uuid,
                "vital_uuids":       vital_uuids,
                "allergy_uuids":     allergy_uuids,
                "condition_uuids":   condition_uuids,
                "medication_uuids":  medication_uuids,
                "errors": {
                    "vitals":     vital_errors,
                    "allergies":  allergy_errors,
                    "conditions": condition_errors,
                    "medications": medication_errors,
                },
            }
            ctx.submissions.mark_success(
                record,
                encounter_uuid=openmrs_encounter_uuid,
                observation_uuid=openmrs_observation_uuid,
                response=response_summary,
            )

            # 5) Verify ─────────────────────────────────────────────
            verification = self.verifier.verify(
                encounter_uuid=openmrs_encounter_uuid,
                observation_uuid=openmrs_observation_uuid,
            )
            if verification.get("ok", True):
                ctx.submissions.mark_verified(record)

            # ── Final state on success ────────────────────────────
            ctx.encounters.set_status(encounter, EncounterStatus.pushed)
            ctx.encounters.set_processing_stage(encounter, ProcessingStage.submitted)

            ctx.audit.append(
                encounter_id=encounter.id,
                event_type="openmrs.submitted",
                agent_name=self.name,
                actor=ctx.actor,
                summary=(
                    f"Submitted SOAP v{note.version} to OpenMRS · "
                    f"encounter={openmrs_encounter_uuid} · "
                    f"meds={len(medication_uuids)}/{len(medications)} · "
                    f"allergies={len(allergy_uuids)}/{len(allergies)} · "
                    f"conditions={len(condition_uuids)}/{len(conditions)} · "
                    f"vitals={len(vital_uuids)}/{len(vitals)}"
                ),
                payload={
                    "submission_id":            record.id,
                    "openmrs_encounter_uuid":   openmrs_encounter_uuid,
                    "openmrs_observation_uuid": openmrs_observation_uuid,
                    "verified": verification.get("ok", True),
                    "simulated": settings.OPENMRS_SIMULATE,
                    "counts": {
                        "medications": len(medication_uuids),
                        "allergies":   len(allergy_uuids),
                        "conditions":  len(condition_uuids),
                        "vitals":      len(vital_uuids),
                    },
                    "errors": response_summary["errors"],
                },
            )

            return AgentResult(
                success=True,
                output={
                    "submission_id":            record.id,
                    "openmrs_encounter_uuid":   openmrs_encounter_uuid,
                    "openmrs_observation_uuid": openmrs_observation_uuid,
                    "verified":                 verification.get("ok", True),
                    "medication_uuids":         medication_uuids,
                    "allergy_uuids":            allergy_uuids,
                    "condition_uuids":          condition_uuids,
                    "vital_uuids":              vital_uuids,
                },
                summary={
                    "submission_id":            record.id,
                    "openmrs_encounter_uuid":   openmrs_encounter_uuid,
                    "openmrs_observation_uuid": openmrs_observation_uuid,
                    "verified":                 verification.get("ok", True),
                    "attempts":                 record.attempts,
                    "simulated":                settings.OPENMRS_SIMULATE,
                    "medications_written":      len(medication_uuids),
                    "allergies_written":        len(allergy_uuids),
                    "conditions_written":       len(condition_uuids),
                    "vitals_written":           len(vital_uuids),
                    "entity_errors":            response_summary["errors"],
                },
            )

        except Exception as exc:  # noqa: BLE001
            err = f"{exc.__class__.__name__}: {exc}"
            ctx.submissions.mark_failed(record, err)
            ctx.audit.append(
                encounter_id=encounter.id,
                event_type="openmrs.submission_failed",
                agent_name=self.name,
                actor=ctx.actor,
                severity="error",
                summary=err,
                payload={"submission_id": record.id, "attempts": record.attempts},
            )
            raise
