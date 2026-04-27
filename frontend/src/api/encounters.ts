import request from "./client"

// ── Types ─────────────────────────────────────────────────────────────────────

export type EncounterStatus = "pending" | "approved" | "pushed"

export interface EncounterListItem {
  id:           string
  patient_name: string
  patient_id:   string
  date:         string
  time:         string
  duration:     string | null
  status:       EncounterStatus
  snippet:      string | null
}

export interface Medication {
  id?:        number
  name:       string
  dose?:      string
  route?:     string
  frequency?: string
  start_date?: string
}

export interface Allergy {
  id?:      number
  allergen: string
  reaction?: string
  severity?: string
}

export interface Diagnosis {
  id?:          number
  icd10_code?:  string
  description:  string
  status?:      string
}

export interface EncounterDetail extends EncounterListItem {
  openmrs_uuid: string | null
  transcript:   string | null
  created_at:   string
  updated_at:   string
  medications:  Medication[]
  allergies:    Allergy[]
  diagnoses:    Diagnosis[]
}

export interface EncounterUpdate {
  transcript?:  string
  medications?: Medication[]
  allergies?:   Allergy[]
  diagnoses?:   Diagnosis[]
}

export interface ChatMessage {
  role:    "user" | "assistant"
  content: string
}

// ── Encounters ────────────────────────────────────────────────────────────────

export const listEncounters = (params?: { status?: string; search?: string }) => {
  const qs = new URLSearchParams()
  if (params?.status) qs.set("status", params.status)
  if (params?.search) qs.set("search", params.search)
  const q = qs.toString()
  return request<{ data: EncounterListItem[] }>(`/encounters${q ? `?${q}` : ""}`)
}

export const getEncounter = (id: string) =>
  request<EncounterDetail>(`/encounters/${id}`)

export const updateEncounter = (id: string, body: EncounterUpdate) =>
  request<EncounterDetail>(`/encounters/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })

export const approveEncounter = (id: string) =>
  request<{ id: string; status: EncounterStatus; updated_at: string }>(
    `/encounters/${id}/approve`, { method: "PATCH" }
  )

export const revertEncounter = (id: string) =>
  request<{ id: string; status: EncounterStatus; updated_at: string }>(
    `/encounters/${id}/revert`, { method: "PATCH" }
  )

export const deleteEncounter = (id: string) =>
  request<void>(`/encounters/${id}`, { method: "DELETE" })

export const pushToOpenMRS = (id: string, openmrs_patient_uuid: string) =>
  request(`/encounters/${id}/push`, {
    method: "POST",
    body: JSON.stringify({ openmrs_patient_uuid }),
  })

// ── AI Chat ───────────────────────────────────────────────────────────────────

export const sendChatMessage = (id: string, message: string, history: ChatMessage[]) =>
  request<{ reply: string; message_id: number }>(`/encounters/${id}/chat`, {
    method: "POST",
    body: JSON.stringify({ message, history }),
  })

// ── Pipeline ──────────────────────────────────────────────────────────────────

const BASE = "http://localhost:8000"

export const createEncounter = async (patient_name: string, patient_id: string) => {
  const form = new FormData()
  form.append("patient_name", patient_name)
  form.append("patient_id", patient_id)
  const res = await fetch(`${BASE}/encounters`, { method: "POST", body: form })
  if (!res.ok) throw new Error("Failed to create encounter")
  return res.json() as Promise<{ id: string; patient_name: string; patient_id: string }>
}

export const transcribeAudio = async (id: string, blob: Blob) => {
  const form = new FormData()
  form.append("audio", blob, "recording.webm")
  const res = await fetch(`${BASE}/encounters/${id}/transcribe`, { method: "POST", body: form })
  if (!res.ok) throw new Error("Transcription failed")
  return res.json() as Promise<{ id: string; transcript: string; duration: string }>
}

export const transcribeEncounter = (id: string) =>
  request<{ id: string; transcript: string; duration: string }>(
    `/encounters/${id}/transcribe`, { method: "POST" }
  )

export const generateNote = (id: string) =>
  request(`/encounters/${id}/generate`, { method: "POST" })

export const formatEncounter = (id: string) =>
  request<{ id: string; transcript: string; duration: string }>(
    `/encounters/${id}/format`, { method: "POST" }
  )

// ── Stats ─────────────────────────────────────────────────────────────────────

export interface Stats {
  notes_today:       number
  pending_review:    number
  pushed_to_openmrs: number
  total_transcripts: number
}

export const getStats = () => request<Stats>("/encounters/stats")
