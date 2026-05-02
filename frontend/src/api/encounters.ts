import request, { API_BASE, ApiError } from "./client"
import type {
  AuditEvent,
  DashboardStats,
  EncounterDetail,
  EncounterListItem,
  Medication,
  PipelineStatus,
  RegisteredAgent,
  RunPipelineResponse,
} from "./types"

export type {
  AgentRun,
  AgentRunStatus,
  Allergy,
  AuditEvent,
  Condition,
  DashboardStats,
  EncounterDetail,
  EncounterListItem,
  EncounterStatus,
  FollowUp,
  Medication,
  PatientContextSnapshot,
  PipelineStatus,
  ProcessingStage,
  RegisteredAgent,
  RunPipelineResponse,
  SoapSections,
  SubmissionInfo,
  Transcript,
  VitalSign,
} from "./types"

export { ApiError }

// Backwards-compatibility aliases used by older pages
export type Stats = DashboardStats

// ── Encounters ────────────────────────────────────────────────────────

export const listEncounters = (params?: { status?: string; search?: string }) => {
  const qs = new URLSearchParams()
  if (params?.status) qs.set("status", params.status)
  if (params?.search) qs.set("search", params.search)
  const q = qs.toString()
  return request<{ data: EncounterListItem[] }>(`/encounters${q ? `?${q}` : ""}`)
}

export const getEncounter = (id: string) =>
  request<EncounterDetail>(`/encounters/${id}`)

export const getStats = () =>
  request<DashboardStats>(`/encounters/stats`)

export const deleteEncounter = (id: string) =>
  request<void>(`/encounters/${id}`, { method: "DELETE" })

/** Bulk-delete encounters. Pass `status` to limit the reset to one bucket
 *  (e.g. "failed" or "pushed"); omit it to delete every encounter. */
export const resetEncounters = (status?: "pending" | "approved" | "pushed" | "failed") => {
  const qs = status ? `?status=${encodeURIComponent(status)}` : ""
  return request<{ deleted: number; status: string | null }>(
    `/encounters/reset${qs}`,
    { method: "POST" },
  )
}

export const createEncounter = async (
  patient_name: string,
  patient_id: string,
  openmrs_patient_uuid?: string,
) => {
  const form = new FormData()
  form.append("patient_name", patient_name)
  form.append("patient_id", patient_id)
  if (openmrs_patient_uuid) form.append("openmrs_patient_uuid", openmrs_patient_uuid)
  const res = await fetch(`${API_BASE}/encounters`, { method: "POST", body: form })
  if (!res.ok) throw new ApiError(`Failed to create encounter: ${res.status}`, res.status)
  return (await res.json()) as {
    id: string
    patient_name: string
    patient_id: string
    status: string
    processing_stage: string
    created_at: string
  }
}

// ── Intake (audio upload + auto-pipeline) ─────────────────────────────

export const intakeAudio = async (
  id: string,
  blob: Blob,
  opts?: { filename?: string; autoRun?: boolean },
) => {
  const form = new FormData()
  form.append("audio", blob, opts?.filename ?? "recording.webm")
  const url = `${API_BASE}/encounters/${id}/intake?auto_run=${opts?.autoRun !== false}`
  const res = await fetch(url, { method: "POST", body: form })
  if (!res.ok) {
    let detail: string = "Intake failed"
    try { detail = (await res.json()).detail ?? detail } catch { /* */ }
    throw new ApiError(detail, res.status)
  }
  return (await res.json()) as RunPipelineResponse
}

// ── Transcript import (any file: txt / md / pdf / docx / srt / vtt / json / html / audio) ──

export const importTranscript = async (
  id: string,
  file: File,
  opts?: { autoRun?: boolean },
) => {
  const form = new FormData()
  form.append("file", file, file.name)
  const url = `${API_BASE}/encounters/${id}/import-transcript?auto_run=${opts?.autoRun !== false}`
  const res = await fetch(url, { method: "POST", body: form })
  if (!res.ok) {
    let detail = "Transcript import failed"
    try { detail = (await res.json()).detail ?? detail } catch { /* */ }
    throw new ApiError(detail, res.status)
  }
  return (await res.json()) as RunPipelineResponse
}

// ── Pipeline / agent control ──────────────────────────────────────────

export const runFullPipeline = (id: string) =>
  request<RunPipelineResponse>(`/encounters/${id}/run`, { method: "POST" })

export const transcribeEncounter = (id: string) =>
  request(`/encounters/${id}/transcribe`, { method: "POST" })

export const generateSoap = (id: string) =>
  request<{
    soap_note_id: number
    subjective: string
    objective: string
    assessment: string
    plan: string
    medications_extracted: number
  }>(`/encounters/${id}/generate-soap`, { method: "POST" })

export const extractMedications = (id: string) =>
  request<Record<string, unknown>>(`/encounters/${id}/extract-medications`, { method: "POST" })

export const getPipelineStatus = (id: string) =>
  request<PipelineStatus>(`/encounters/${id}/pipeline`)

// ── Physician review ──────────────────────────────────────────────────

export const openReview = (id: string) =>
  request(`/encounters/${id}/review/open`, { method: "POST" })

export interface SoapEditPayload {
  sections?: {
    subjective?: string
    objective?: string
    assessment?: string
    plan?: string
  }
  medications?: Array<Partial<Medication> & { name: string }>
  actor?: string
}

export const editSoap = (id: string, body: SoapEditPayload) =>
  request(`/encounters/${id}/review/edit`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })

export const approveSoap = (id: string, opts?: { actor?: string; comments?: string }) =>
  request<{ encounter_id: string; soap_note_id: number; approved_at: string; edits_made: number }>(
    `/encounters/${id}/review/approve`,
    { method: "POST", body: JSON.stringify({ actor: opts?.actor ?? "physician", comments: opts?.comments ?? null }) },
  )

export const revertApproval = (id: string) =>
  request(`/encounters/${id}/review/revert`, { method: "POST" })

// ── OpenMRS submission ────────────────────────────────────────────────

export const submitToOpenMRS = (id: string, opts?: {
  openmrs_patient_uuid?: string
  practitioner_uuid?: string
  actor?: string
}) =>
  request<{
    encounter_id: string
    submission_id: number
    status: string
    openmrs_encounter_uuid: string | null
    openmrs_observation_uuid: string | null
    attempts: number
    error?: string | null
  }>(`/encounters/${id}/submit`, {
    method: "POST",
    body: JSON.stringify({
      openmrs_patient_uuid: opts?.openmrs_patient_uuid ?? null,
      practitioner_uuid:    opts?.practitioner_uuid    ?? null,
      actor:                opts?.actor                ?? "physician",
    }),
  })

// ── Patient context ───────────────────────────────────────────────────

export const refreshPatientContext = (id: string) =>
  request<{ encounter_id: string; snapshot_id: number; patient_uuid: string }>(
    `/encounters/${id}/patient-context/refresh`,
    { method: "POST" },
  )

// ── Audit / Agents ────────────────────────────────────────────────────

export const getAuditTrail = (id: string) =>
  request<{ encounter_id: string; events: AuditEvent[] }>(`/encounters/${id}/audit`)

export const getAuditTimeline = (id: string) =>
  request<{
    encounter_id: string
    events_count: number
    runs_count: number
    timeline: Array<Record<string, unknown>>
    rollup: Record<string, { runs: number; succeeded: number; failed: number; total_ms: number }>
  }>(`/encounters/${id}/audit/timeline`)

export const listRegisteredAgents = () =>
  request<{ agents: RegisteredAgent[] }>(`/agents`)

// ── AI chat (legacy, kept for compatibility) ──────────────────────────

export interface ChatMessage { role: "user" | "assistant"; content: string }

export const sendChatMessage = (id: string, message: string, history: ChatMessage[]) =>
  request<{ reply: string }>(`/encounters/${id}/chat`, {
    method: "POST",
    body: JSON.stringify({ message, history }),
  })

// Legacy exports still referenced by older pages — they re-route to
// the new endpoints so existing components keep working until removed.
export const transcribeAudio = (id: string, blob: Blob) =>
  intakeAudio(id, blob, { autoRun: false })

export const generateNote = (id: string) => generateSoap(id)
export const formatEncounter = (id: string) => transcribeEncounter(id)
export const updateEncounter = (id: string, body: SoapEditPayload) => editSoap(id, body)
export const approveEncounter = (id: string) => approveSoap(id)
export const revertEncounter = (id: string) => revertApproval(id)
export const pushToOpenMRS = (id: string, openmrs_patient_uuid: string) =>
  submitToOpenMRS(id, { openmrs_patient_uuid })
