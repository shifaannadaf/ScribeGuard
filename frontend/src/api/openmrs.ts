import request from "./client"

// ── Types ──────────────────────────────────────────────────────────────────

export interface OpenMRSPatient {
  uuid:       string
  name:       string
  identifier: string
  birthdate:  string | null
  gender:     string | null
  address:    string | null
}

export interface OmrsAllergy {
  uuid:     string
  allergen: string
  reaction: string
  severity: string
  status:   string
}

export interface OmrsCondition {
  uuid:         string
  display:      string
  icd10:        string | null
  status:       string
  recordedDate: string | null
}

export interface OmrsVitals {
  height:      number | null
  weight:      number | null
  temperature: number | null
  spO2:        number | null
  respRate:    number | null
}

export interface OmrsMedication {
  uuid:       string
  name:       string
  dose:       string | null
  status:     string
  authoredOn: string | null
}

export interface OmrsEncounter {
  uuid:   string
  type:   string
  date:   string | null
  status: string
}

// ── Parsers ────────────────────────────────────────────────────────────────

function parsePatientResource(r: any): OpenMRSPatient {
  const given  = r.name?.[0]?.given?.join(" ") ?? ""
  const family = r.name?.[0]?.family ?? ""
  const addr   = r.address?.[0]
  const address = addr
    ? [addr.city, addr.state, addr.country].filter(Boolean).join(", ")
    : null
  return {
    uuid:       r.id,
    name:       `${given} ${family}`.trim(),
    identifier: r.identifier?.[0]?.value ?? "",
    birthdate:  r.birthDate ?? null,
    gender:     r.gender ?? null,
    address,
  }
}

function parsePatientList(bundle: any): OpenMRSPatient[] {
  if (!bundle?.entry?.length) return []
  return bundle.entry.map((e: any) => parsePatientResource(e.resource))
}


function parseAllergies(bundle: any): OmrsAllergy[] {
  if (!bundle?.entry?.length) return []
  return bundle.entry.map((e: any) => {
    const r = e.resource
    return {
      uuid:     r.id,
      allergen: r.code?.text ?? r.code?.coding?.[0]?.display ?? "Unknown",
      reaction: r.reaction?.[0]?.manifestation?.[0]?.text
             ?? r.reaction?.[0]?.manifestation?.[0]?.coding?.[0]?.display
             ?? "—",
      severity: r.reaction?.[0]?.severity ?? "unknown",
      status:   r.clinicalStatus?.coding?.[0]?.code ?? "active",
    }
  })
}

function parseConditions(bundle: any): OmrsCondition[] {
  if (!bundle?.entry?.length) return []
  return bundle.entry.map((e: any) => {
    const r    = e.resource
    const icd10 = r.code?.coding?.find((c: any) =>
      c.system?.includes("icd") || c.system?.includes("ICD")
    )?.code ?? null
    return {
      uuid:         r.id,
      display:      r.code?.text ?? r.code?.coding?.[0]?.display ?? "Unknown",
      icd10,
      status:       r.clinicalStatus?.coding?.[0]?.code ?? "active",
      recordedDate: r.recordedDate ?? null,
    }
  })
}

const VITAL_MAP: Record<string, keyof OmrsVitals> = {
  "5090AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA": "height",
  "5089AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA": "weight",
  "5088AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA": "temperature",
  "5092AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA": "spO2",
  "5242AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA": "respRate",
}

function parseVitals(bundle: any): OmrsVitals {
  const v: OmrsVitals = { height: null, weight: null, temperature: null, spO2: null, respRate: null }
  if (!bundle?.entry?.length) return v
  for (const e of bundle.entry) {
    const r    = e.resource
    const code = r.code?.coding?.[0]?.code
    const key  = code ? VITAL_MAP[code] : null
    if (key && r.valueQuantity?.value != null) v[key] = r.valueQuantity.value
  }
  return v
}

function parseMedications(bundle: any): OmrsMedication[] {
  if (!bundle?.entry?.length) return []
  return bundle.entry.map((e: any) => {
    const r = e.resource
    return {
      uuid:       r.id,
      name:       r.medicationReference?.display
               ?? r.medicationCodeableConcept?.text
               ?? "Unknown",
      dose:       r.dosageInstruction?.[0]?.text ?? null,
      status:     r.status ?? "unknown",
      authoredOn: r.authoredOn ?? null,
    }
  })
}

function parseEncounters(bundle: any): OmrsEncounter[] {
  if (!bundle?.entry?.length) return []
  return bundle.entry.map((e: any) => {
    const r = e.resource
    return {
      uuid:   r.id,
      type:   r.type?.[0]?.text ?? r.type?.[0]?.coding?.[0]?.display ?? "Visit",
      date:   r.period?.start ?? null,
      status: r.status ?? "unknown",
    }
  })
}

// ── Read ───────────────────────────────────────────────────────────────────

export async function searchPatients(query: string): Promise<OpenMRSPatient[]> {
  const bundle = await request<any>(`/openmrs/patient?q=${encodeURIComponent(query)}`)
  return parsePatientList(bundle)
}

export async function searchPatientByIdentifier(identifier: string): Promise<OpenMRSPatient | null> {
  const results = await searchPatients(identifier)
  return results[0] ?? null
}

export async function fetchAllergies(uuid: string): Promise<OmrsAllergy[]> {
  const b = await request<any>(`/openmrs/allergy?patient_uuid=${encodeURIComponent(uuid)}`)
  return parseAllergies(b)
}

export async function fetchConditions(uuid: string): Promise<OmrsCondition[]> {
  const b = await request<any>(`/openmrs/condition?patient_uuid=${encodeURIComponent(uuid)}`)
  return parseConditions(b)
}

export async function fetchVitals(uuid: string): Promise<OmrsVitals> {
  const b = await request<any>(`/openmrs/observation?patient_uuid=${encodeURIComponent(uuid)}`)
  return parseVitals(b)
}

export async function fetchMedications(uuid: string): Promise<OmrsMedication[]> {
  const b = await request<any>(`/openmrs/medication-request?patient_uuid=${encodeURIComponent(uuid)}`)
  return parseMedications(b)
}

export async function fetchEncounters(uuid: string): Promise<OmrsEncounter[]> {
  const b = await request<any>(`/openmrs/encounter?patient_uuid=${encodeURIComponent(uuid)}`)
  return parseEncounters(b)
}

// ── Write ──────────────────────────────────────────────────────────────────

export async function addAllergy(
  patientUuid: string,
  allergen: string,
  reaction: string,
  severity: string,
): Promise<void> {
  await request<any>("/openmrs/allergy", {
    method: "POST",
    body: JSON.stringify({
      patient_uuid:          patientUuid,
      substance_display:     allergen,
      manifestation_display: reaction,
      severity,
    }),
  })
}

export async function removeAllergy(uuid: string): Promise<void> {
  await request<any>(`/openmrs/allergy/${uuid}`, { method: "DELETE" })
}

export async function addCondition(
  patientUuid: string,
  display: string,
  icd10: string,
): Promise<void> {
  await request<any>("/openmrs/condition", {
    method: "POST",
    body: JSON.stringify({
      patient_uuid:  patientUuid,
      icd10_code:    icd10 || "Z99.9",
      snomed_code:   "73211009",
      display,
      recorded_date: new Date().toISOString().split("T")[0],
    }),
  })
}

export async function removeCondition(uuid: string): Promise<void> {
  await request<any>(`/openmrs/condition/${uuid}`, { method: "DELETE" })
}

export async function stopMedication(uuid: string): Promise<void> {
  await request<any>(`/openmrs/medication-request/${uuid}`, {
    method: "PATCH",
    body: JSON.stringify({
      json_patch: [{ op: "replace", path: "/status", value: "stopped" }],
    }),
  })
}
