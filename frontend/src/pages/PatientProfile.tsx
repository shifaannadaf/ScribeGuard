import { useState, useEffect } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Loader2, UserRound, Trash2, Plus, X,
  Activity, ShieldAlert, Stethoscope, Pill, CalendarDays
} from 'lucide-react'
import {
  searchPatientByIdentifier,
  fetchAllergies, fetchConditions, fetchVitals,
  fetchMedications, fetchEncounters,
  addAllergy, removeAllergy,
  addCondition, removeCondition,
  stopMedication,
  type OpenMRSPatient, type OmrsAllergy, type OmrsCondition,
  type OmrsVitals, type OmrsMedication, type OmrsEncounter,
} from '../api/openmrs'

// ── Small helpers ──────────────────────────────────────────────────────────

function fmt(date: string | null) {
  if (!date) return '—'
  try {
    const d = date.includes('T') ? new Date(date) : new Date(date + 'T12:00:00')
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
  } catch { return date }
}

function severityColor(s: string) {
  if (s === 'severe')   return 'text-red-400'
  if (s === 'moderate') return 'text-yellow-400'
  return 'text-green-400'
}

function statusBadge(s: string) {
  const base = 'text-xs px-2 py-0.5 rounded-full font-medium'
  if (s === 'active')   return `${base} bg-green-500/15 text-green-400`
  if (s === 'stopped' || s === 'inactive') return `${base} bg-gray-700 text-gray-400`
  return `${base} bg-blue-500/15 text-blue-400`
}

// ── Section card wrapper ───────────────────────────────────────────────────

function Section({ icon: Icon, title, children }: {
  icon: React.ElementType, title: string, children: React.ReactNode
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-gray-800">
        <Icon size={16} className="text-blue-400 shrink-0" />
        <h2 className="text-white text-sm font-semibold">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}

// ── Add-row inline forms ───────────────────────────────────────────────────

function AddAllergyRow({ onAdd }: { onAdd: (a: string, r: string, s: string) => Promise<void> }) {
  const [open, setOpen]       = useState(false)
  const [allergen, setAllergen] = useState('')
  const [reaction, setReaction] = useState('')
  const [severity, setSeverity] = useState('moderate')
  const [saving,   setSaving]   = useState(false)

  async function submit() {
    if (!allergen.trim() || !reaction.trim()) return
    setSaving(true)
    await onAdd(allergen.trim(), reaction.trim(), severity)
    setAllergen(''); setReaction(''); setSeverity('moderate'); setOpen(false); setSaving(false)
  }

  if (!open) return (
    <button onClick={() => setOpen(true)}
      className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 text-xs mt-3 transition-colors cursor-pointer">
      <Plus size={13} /> Add allergy
    </button>
  )

  return (
    <div className="mt-3 flex flex-wrap gap-2 items-end bg-gray-800/50 rounded-lg p-3">
      <input value={allergen} onChange={e => setAllergen(e.target.value)} placeholder="Allergen"
        className="bg-gray-800 border border-gray-700 text-gray-200 placeholder-gray-600 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-600 w-36" />
      <input value={reaction} onChange={e => setReaction(e.target.value)} placeholder="Reaction"
        className="bg-gray-800 border border-gray-700 text-gray-200 placeholder-gray-600 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-600 w-36" />
      <select value={severity} onChange={e => setSeverity(e.target.value)}
        className="bg-gray-800 border border-gray-700 text-gray-200 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-600">
        <option value="mild">Mild</option>
        <option value="moderate">Moderate</option>
        <option value="severe">Severe</option>
      </select>
      <button onClick={submit} disabled={saving || !allergen.trim() || !reaction.trim()}
        className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-xs px-3 py-2 rounded-lg transition-colors cursor-pointer">
        {saving ? <Loader2 size={12} className="animate-spin" /> : 'Save'}
      </button>
      <button onClick={() => setOpen(false)} className="text-gray-500 hover:text-white transition-colors cursor-pointer"><X size={14} /></button>
    </div>
  )
}

function AddConditionRow({ onAdd }: { onAdd: (d: string, c: string) => Promise<void> }) {
  const [open,    setOpen]    = useState(false)
  const [display, setDisplay] = useState('')
  const [icd10,   setIcd10]   = useState('')
  const [saving,  setSaving]  = useState(false)

  async function submit() {
    if (!display.trim()) return
    setSaving(true)
    await onAdd(display.trim(), icd10.trim())
    setDisplay(''); setIcd10(''); setOpen(false); setSaving(false)
  }

  if (!open) return (
    <button onClick={() => setOpen(true)}
      className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 text-xs mt-3 transition-colors cursor-pointer">
      <Plus size={13} /> Add condition
    </button>
  )

  return (
    <div className="mt-3 flex flex-wrap gap-2 items-end bg-gray-800/50 rounded-lg p-3">
      <input value={display} onChange={e => setDisplay(e.target.value)} placeholder="Condition name"
        className="bg-gray-800 border border-gray-700 text-gray-200 placeholder-gray-600 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-600 w-48" />
      <input value={icd10} onChange={e => setIcd10(e.target.value)} placeholder="ICD-10 (optional)"
        className="bg-gray-800 border border-gray-700 text-gray-200 placeholder-gray-600 text-xs rounded-lg px-3 py-2 outline-none focus:border-blue-600 w-32" />
      <button onClick={submit} disabled={saving || !display.trim()}
        className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-xs px-3 py-2 rounded-lg transition-colors cursor-pointer">
        {saving ? <Loader2 size={12} className="animate-spin" /> : 'Save'}
      </button>
      <button onClick={() => setOpen(false)} className="text-gray-500 hover:text-white transition-colors cursor-pointer"><X size={14} /></button>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export default function PatientProfile() {
  const { uuid }      = useParams<{ uuid: string }>()
  const location      = useLocation()
  const navigate      = useNavigate()

  const [patient,    setPatient]    = useState<OpenMRSPatient | null>(location.state?.patient ?? null)
  const [allergies,  setAllergies]  = useState<OmrsAllergy[]>([])
  const [conditions, setConditions] = useState<OmrsCondition[]>([])
  const [vitals,     setVitals]     = useState<OmrsVitals | null>(null)
  const [meds,       setMeds]       = useState<OmrsMedication[]>([])
  const [encounters, setEncounters] = useState<OmrsEncounter[]>([])
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)

  useEffect(() => {
    if (!uuid) return
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [p, a, c, v, m, e] = await Promise.all([
          patient ? Promise.resolve(patient) : searchPatientByIdentifier(uuid!),
          fetchAllergies(uuid!).catch(() => []),
          fetchConditions(uuid!).catch(() => []),
          fetchVitals(uuid!).catch(() => null),
          fetchMedications(uuid!).catch(() => []),
          fetchEncounters(uuid!).catch(() => []),
        ])
        if (!p) { setError('Patient not found.'); return }
        setPatient(p)
        setAllergies(a)
        setConditions(c)
        setVitals(v)
        setMeds(m)
        setEncounters(e)
      } catch {
        setError('Failed to load patient data. Check that OpenMRS is running.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [uuid])

  async function handleAddAllergy(allergen: string, reaction: string, severity: string) {
    if (!uuid) return
    await addAllergy(uuid, allergen, reaction, severity)
    setAllergies(await fetchAllergies(uuid))
  }

  async function handleRemoveAllergy(allergyUuid: string) {
    await removeAllergy(allergyUuid)
    setAllergies(prev => prev.filter(a => a.uuid !== allergyUuid))
  }

  async function handleAddCondition(display: string, icd10: string) {
    if (!uuid) return
    await addCondition(uuid, display, icd10)
    setConditions(await fetchConditions(uuid))
  }

  async function handleRemoveCondition(condUuid: string) {
    await removeCondition(condUuid)
    setConditions(prev => prev.filter(c => c.uuid !== condUuid))
  }

  async function handleStopMed(medUuid: string) {
    await stopMedication(medUuid)
    setMeds(prev => prev.map(m => m.uuid === medUuid ? { ...m, status: 'stopped' } : m))
  }

  const activeMeds = meds.filter(m => m.status === 'active')
  const pastMeds   = meds.filter(m => m.status !== 'active')

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <Loader2 size={28} className="text-blue-400 animate-spin" />
    </div>
  )

  if (error) return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <p className="text-red-400 text-sm">{error}</p>
      <button onClick={() => navigate('/patients')}
        className="text-gray-400 hover:text-white text-sm flex items-center gap-2 cursor-pointer transition-colors">
        <ArrowLeft size={15} /> Back to search
      </button>
    </div>
  )

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="px-8 py-6 shrink-0">

        {/* Back */}
        <button onClick={() => navigate('/patients')}
          className="flex items-center gap-2 text-gray-500 hover:text-white text-sm mb-5 transition-colors cursor-pointer">
          <ArrowLeft size={15} /> All Patients
        </button>

        {/* Patient header */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-center gap-5 mb-6">
          <div className="w-14 h-14 rounded-full bg-blue-500/15 flex items-center justify-center shrink-0">
            <UserRound size={26} className="text-blue-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-white text-xl font-semibold">{patient?.name}</h1>
            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1">
              <span className="text-gray-400 text-sm">ID: <span className="text-gray-300">{patient?.identifier}</span></span>
              <span className="text-gray-400 text-sm">DOB: <span className="text-gray-300">{fmt(patient?.birthdate ?? null)}</span></span>
              <span className="text-gray-400 text-sm">Sex: <span className="text-gray-300">{patient?.gender?.toUpperCase() ?? '—'}</span></span>
              {patient?.address && <span className="text-gray-400 text-sm">Location: <span className="text-gray-300">{patient.address}</span></span>}
            </div>
          </div>
        </div>

        {/* Vitals row */}
        {vitals && (
          <Section icon={Activity} title="Latest Vitals">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {([
                { label: 'Height',      value: vitals.height,      unit: 'cm'  },
                { label: 'Weight',      value: vitals.weight,      unit: 'kg'  },
                { label: 'Temperature', value: vitals.temperature, unit: '°C'  },
                { label: 'SpO₂',        value: vitals.spO2,        unit: '%'   },
                { label: 'Resp Rate',   value: vitals.respRate,    unit: '/min' },
              ] as const).map(({ label, value, unit }) => (
                <div key={label} className="bg-gray-800/60 rounded-lg p-3 text-center">
                  <p className="text-gray-500 text-xs mb-1">{label}</p>
                  <p className="text-white text-lg font-semibold">
                    {value != null ? value : '—'}
                    {value != null && <span className="text-gray-500 text-xs ml-1">{unit}</span>}
                  </p>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Allergies + Conditions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mt-5">

          {/* Allergies */}
          <Section icon={ShieldAlert} title="Allergies">
            {allergies.length === 0 ? (
              <p className="text-gray-600 text-sm">No allergies recorded.</p>
            ) : (
              <div className="flex flex-col divide-y divide-gray-800">
                {allergies.map(a => (
                  <div key={a.uuid} className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0">
                    <div>
                      <p className="text-gray-200 text-sm font-medium">{a.allergen}</p>
                      <p className="text-gray-500 text-xs mt-0.5">
                        {a.reaction} · <span className={severityColor(a.severity)}>{a.severity}</span>
                      </p>
                    </div>
                    <button onClick={() => handleRemoveAllergy(a.uuid)}
                      className="text-gray-700 hover:text-red-400 transition-colors ml-3 cursor-pointer shrink-0">
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <AddAllergyRow onAdd={handleAddAllergy} />
          </Section>

          {/* Conditions */}
          <Section icon={Stethoscope} title="Conditions">
            {conditions.length === 0 ? (
              <p className="text-gray-600 text-sm">No conditions recorded.</p>
            ) : (
              <div className="flex flex-col divide-y divide-gray-800">
                {conditions.map(c => (
                  <div key={c.uuid} className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0">
                    <div>
                      <p className="text-gray-200 text-sm font-medium">{c.display}</p>
                      <p className="text-gray-500 text-xs mt-0.5">
                        {c.icd10 && <span className="mr-2">{c.icd10}</span>}
                        <span className={statusBadge(c.status)}>{c.status}</span>
                        {c.recordedDate && <span className="ml-2">{fmt(c.recordedDate)}</span>}
                      </p>
                    </div>
                    <button onClick={() => handleRemoveCondition(c.uuid)}
                      className="text-gray-700 hover:text-red-400 transition-colors ml-3 cursor-pointer shrink-0">
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <AddConditionRow onAdd={handleAddCondition} />
          </Section>
        </div>

        {/* Active Medications */}
        <div className="mt-5">
          <Section icon={Pill} title="Active Medications">
            {activeMeds.length === 0 ? (
              <p className="text-gray-600 text-sm">No active medications.</p>
            ) : (
              <div className="flex flex-col divide-y divide-gray-800">
                {activeMeds.map(m => (
                  <div key={m.uuid} className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0">
                    <div>
                      <p className="text-gray-200 text-sm font-medium">{m.name}</p>
                      {m.dose && <p className="text-gray-500 text-xs mt-0.5">{m.dose}</p>}
                    </div>
                    <button onClick={() => handleStopMed(m.uuid)}
                      className="text-xs text-gray-500 hover:text-red-400 border border-gray-700 hover:border-red-500/50 px-3 py-1 rounded-lg transition-colors cursor-pointer ml-3 shrink-0">
                      Stop
                    </button>
                  </div>
                ))}
              </div>
            )}
          </Section>
        </div>

        {/* Past Medications */}
        {pastMeds.length > 0 && (
          <div className="mt-5">
            <Section icon={Pill} title="Past Medications">
              <div className="flex flex-col divide-y divide-gray-800">
                {pastMeds.map(m => (
                  <div key={m.uuid} className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0 opacity-60">
                    <div>
                      <p className="text-gray-400 text-sm">{m.name}</p>
                      {m.dose && <p className="text-gray-600 text-xs mt-0.5">{m.dose}</p>}
                    </div>
                    <span className={statusBadge(m.status)}>{m.status}</span>
                  </div>
                ))}
              </div>
            </Section>
          </div>
        )}

        {/* Visits */}
        {encounters.length > 0 && (
          <div className="mt-5 mb-8">
            <Section icon={CalendarDays} title="Visit History">
              <div className="flex flex-col divide-y divide-gray-800">
                {encounters.map(e => (
                  <div key={e.uuid} className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0">
                    <div>
                      <p className="text-gray-200 text-sm">{e.type}</p>
                      <p className="text-gray-500 text-xs mt-0.5">{fmt(e.date)}</p>
                    </div>
                    <span className={statusBadge(e.status)}>{e.status}</span>
                  </div>
                ))}
              </div>
            </Section>
          </div>
        )}

      </div>
    </div>
  )
}
