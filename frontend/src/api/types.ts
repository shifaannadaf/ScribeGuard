// ── Domain types mirrored from the backend Pydantic schemas ────────────

export type EncounterStatus = "pending" | "approved" | "pushed" | "failed"

export type ProcessingStage =
  | "created"
  | "audio_received"
  | "transcribing"
  | "transcribed"
  | "generating_soap"
  | "soap_drafted"
  | "extracting_meds"
  | "ready_for_review"
  | "in_review"
  | "approved"
  | "submitting"
  | "submitted"
  | "failed"

export interface EncounterListItem {
  id: string
  patient_name: string
  patient_id: string
  date: string
  time: string
  created_at: string | null
  duration: string | null
  status: EncounterStatus
  processing_stage: ProcessingStage
  snippet: string | null
  has_soap_note: boolean
  medication_count: number
  submitted: boolean
}

export interface Transcript {
  id: number
  raw_text: string
  formatted_text: string | null
  duration_seconds: number | null
  model: string
  quality_score: number | null
  quality_issues: string[] | null
  word_count: number | null
  created_at: string
}

export interface SoapSections {
  id: number
  version: number
  is_current: boolean
  subjective: string
  objective: string
  assessment: string
  plan: string
  status: string
  low_confidence_sections: string[] | null
  flags: Record<string, unknown> | null
  model: string
  created_at: string
  updated_at: string
}

export interface Medication {
  id: number
  name: string
  dose: string | null
  route: string | null
  frequency: string | null
  duration: string | null
  start_date: string | null
  indication: string | null
  raw_text: string | null
  confidence: string | null
}

export interface Allergy {
  id: number
  substance: string
  reaction: string | null
  severity: string | null
  category: string | null
  onset: string | null
  confidence: string | null
  raw_text: string | null
  openmrs_resource_uuid: string | null
}

export interface Condition {
  id: number
  description: string
  icd10_code: string | null
  snomed_code: string | null
  clinical_status: string | null
  verification: string | null
  onset: string | null
  note: string | null
  confidence: string | null
  raw_text: string | null
  openmrs_resource_uuid: string | null
}

export interface VitalSign {
  id: number
  kind: string
  value: number
  unit: string | null
  measured_at: string | null
  confidence: string | null
  raw_text: string | null
  openmrs_resource_uuid: string | null
}

export interface FollowUp {
  id: number
  description: string
  interval: string | null
  target_date: string | null
  with_provider: string | null
  confidence: string | null
}

export interface PatientContextSnapshot {
  id: number
  fetched_at: string
  patient_uuid: string | null
  patient_demographics: Record<string, unknown> | null
  existing_medications: Array<Record<string, unknown>> | null
  existing_allergies:   Array<Record<string, unknown>> | null
  existing_conditions:  Array<Record<string, unknown>> | null
  recent_observations:  Array<Record<string, unknown>> | null
  recent_encounters:    Array<Record<string, unknown>> | null
  fetch_errors: Record<string, string> | null
}

export interface SubmissionInfo {
  id: number
  status: string
  attempts: number
  openmrs_encounter_uuid: string | null
  openmrs_observation_uuid: string | null
  last_error: string | null
  started_at: string
  completed_at: string | null
}

export interface EncounterDetail {
  id: string
  patient_name: string
  patient_id: string
  openmrs_patient_uuid: string | null
  status: EncounterStatus
  processing_stage: ProcessingStage
  last_error: string | null
  duration: string | null
  audio_filename: string | null
  audio_duration_sec: string | null
  created_at: string
  updated_at: string
  transcript: Transcript | null
  soap_note: SoapSections | null
  medications: Medication[]
  allergies: Allergy[]
  conditions: Condition[]
  vital_signs: VitalSign[]
  follow_ups: FollowUp[]
  patient_context: PatientContextSnapshot | null
  submission: SubmissionInfo | null
}

export interface DashboardStats {
  notes_today: number
  pending_review: number
  pushed_to_openmrs: number
  failed: number
  total_encounters: number
}

// ── Agent run / pipeline types ────────────────────────────────────────

export type AgentRunStatus = "queued" | "running" | "succeeded" | "failed" | "skipped"

export interface AgentRun {
  id: number
  agent_name: string
  agent_version: string | null
  status: AgentRunStatus
  attempt: number
  input_summary: Record<string, unknown> | null
  output_summary: Record<string, unknown> | null
  error_message: string | null
  error_type: string | null
  started_at: string
  finished_at: string | null
  duration_ms: number | null
}

export interface PipelineStatus {
  encounter_id: string
  processing_stage: ProcessingStage
  status: EncounterStatus
  last_error: string | null
  has_audio: boolean
  has_transcript: boolean
  has_soap_note: boolean
  has_approval: boolean
  submitted: boolean
  agent_runs: AgentRun[]
}

export interface RegisteredAgent {
  name: string
  version: string
  description: string
}

export interface RunPipelineResponse {
  encounter_id: string
  final_stage: ProcessingStage
  status: EncounterStatus
  transcript_id: number | null
  soap_note_id: number | null
  medications_extracted: number
  duration_ms: number
  errors: string[]
}

export interface AuditEvent {
  id: number
  event_type: string
  agent_name: string | null
  actor: string
  severity: string
  summary: string | null
  payload: unknown
  created_at: string
}
