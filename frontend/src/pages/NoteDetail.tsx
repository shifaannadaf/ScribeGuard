import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, User, Calendar, Clock, Timer, Loader2, Check, FileText, Lock, Upload, X, Search, Users, UserPlus } from 'lucide-react'
import { 
  getEncounter, updateEncounter, approveEncounter, revertEncounter, unpushEncounter, pushToOpenMRS,
  type EncounterDetail, type Medication, type PastMedication, type Allergy, type Diagnosis, type Vitals
} from '../api/encounters'
import { searchPatients, type OpenMRSPatient } from '../api/openmrs'

type Tab = 'chief' | 'vitals' | 'diagnoses' | 'medications' | 'past_meds' | 'allergies' | 'summary' | 'plan' | 'transcript'

const tabs: { id: Tab; label: string }[] = [
  { id: 'chief',       label: 'Chief Complaint' },
  { id: 'vitals',      label: 'Vitals' },
  { id: 'diagnoses',   label: 'Diagnoses' },
  { id: 'medications', label: 'Active Medications' },
  { id: 'past_meds',   label: 'Past Medications' },
  { id: 'allergies',   label: 'Allergies' },
  { id: 'summary',     label: 'Clinical Summary' },
  { id: 'plan',        label: 'Plan' },
  { id: 'transcript',  label: 'Transcript' },
]

const statusMap = {
  pending:  { label: 'Pending Review', style: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' },
  approved: { label: 'Approved',       style: 'bg-green-500/10 text-green-400 border border-green-500/20' },
  pushed:   { label: 'In OpenMRS',     style: 'bg-blue-500/10 text-blue-400 border border-blue-500/20' },
}

function EditableField({ label, value, onChange, multiline = false, readonly = false, placeholder = '' }: {
  label: string; value: string; onChange: (v: string) => void; multiline?: boolean; readonly?: boolean; placeholder?: string
}) {
  const base = 'text-sm rounded-lg px-3 py-2.5 outline-none transition-colors duration-150'
  const edit = 'bg-gray-800 border border-gray-700 text-gray-200 placeholder:text-gray-600 focus:border-blue-600'
  const read = 'bg-transparent border border-gray-800 text-gray-400 cursor-default select-text'
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-gray-500 text-xs font-medium uppercase tracking-wider">{label}</label>
      {multiline ? (
        <textarea value={value} onChange={e => !readonly && onChange(e.target.value)} readOnly={readonly} rows={3}
          placeholder={placeholder}
          className={`${base} ${readonly ? read : edit} resize-none leading-relaxed`} />
      ) : (
        <input type="text" value={value} onChange={e => !readonly && onChange(e.target.value)} readOnly={readonly}
          placeholder={placeholder}
          className={`${base} ${readonly ? read : edit}`} />
      )}
    </div>
  )
}

function PatientSearchModal({ record, onConfirm, onCancel }: {
  record: EncounterDetail; onConfirm: (patientUuid: string | null) => void; onCancel: () => void
}) {
  const [query, setQuery] = useState(record.patient_name)
  const [searching, setSearching] = useState(false)
  const [patients, setPatients] = useState<OpenMRSPatient[]>([])
  const [searched, setSearched] = useState(false)
  const [selectedPatient, setSelectedPatient] = useState<OpenMRSPatient | null>(null)

  async function handleSearch() {
    if (!query.trim()) return
    setSearching(true)
    try {
      const results = await searchPatients(query)
      setPatients(results)
      setSearched(true)
      if (results.length === 1) {
        setSelectedPatient(results[0])
      }
    } catch (e: any) {
      alert(`Search failed: ${e.message}`)
    } finally {
      setSearching(false)
    }
  }

  function handleConfirm() {
    if (selectedPatient) {
      onConfirm(selectedPatient.uuid)
    } else if (searched && patients.length === 0) {
      // Create new patient
      onConfirm(null)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md mx-4 shadow-xl">
        <div className="flex items-start justify-between mb-4">
          <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center shrink-0">
            <Upload size={20} className="text-blue-400" />
          </div>
          <button onClick={onCancel} className="text-gray-600 hover:text-white transition-colors cursor-pointer">
            <X size={18} />
          </button>
        </div>
        
        <h2 className="text-white text-base font-semibold mb-1">Push to OpenMRS</h2>
        <p className="text-gray-400 text-sm mb-1">
          Pushing note for <span className="text-white font-medium">{record.patient_name}</span>
        </p>
        <p className="text-gray-500 text-xs mb-5">{record.patient_id} · {record.date} · {record.time}</p>

        <label className="text-gray-500 text-xs font-medium uppercase tracking-wider block mb-1.5">
          Search for patient in OpenMRS
        </label>
        
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Enter patient name or ID..."
            className="flex-1 bg-gray-800 border border-gray-700 text-gray-200 placeholder-gray-600 text-sm rounded-lg px-3 py-2.5 outline-none focus:border-blue-600 transition-colors duration-150"
          />
          <button
            onClick={handleSearch}
            disabled={searching || !query.trim()}
            className="px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors duration-150 cursor-pointer flex items-center gap-2"
          >
            {searching ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Search
          </button>
        </div>

        {searched && (
          <div className="mb-4">
            {patients.length === 0 ? (
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-yellow-500/10 flex items-center justify-center shrink-0 mt-0.5">
                    <UserPlus size={16} className="text-yellow-400" />
                  </div>
                  <div className="flex-1">
                    <p className="text-white text-sm font-medium mb-1">Patient not found</p>
                    <p className="text-gray-400 text-xs">
                      No patient found with "{query}". A new patient record will be created in OpenMRS.
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2 mb-2">
                  <Users size={14} className="text-gray-500" />
                  <p className="text-gray-500 text-xs font-medium uppercase tracking-wider">
                    Found {patients.length} patient{patients.length !== 1 ? 's' : ''}
                  </p>
                </div>
                {patients.map(patient => (
                  <button
                    key={patient.uuid}
                    onClick={() => setSelectedPatient(patient)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors duration-150 cursor-pointer ${
                      selectedPatient?.uuid === patient.uuid
                        ? 'bg-blue-500/10 border-blue-500/30 text-white'
                        : 'bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-600'
                    }`}
                  >
                    <p className="text-sm font-medium mb-0.5">{patient.name}</p>
                    <p className="text-xs text-gray-500">
                      ID: {patient.identifier}
                      {patient.birthdate && ` · DOB: ${patient.birthdate}`}
                      {patient.gender && ` · ${patient.gender.toUpperCase()}`}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 text-sm font-medium transition-colors duration-150 cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!searched || (patients.length > 1 && !selectedPatient)}
            className="flex-1 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors duration-150 cursor-pointer"
          >
            {searched && patients.length === 0 ? 'Create & Push' : 'Push'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function NoteDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const readonly = searchParams.get('mode') === 'view'

  const [record, setRecord] = useState<EncounterDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [approving, setApproving] = useState(false)
  const [reverting, setReverting] = useState(false)
  const [pushing, setPushing] = useState(false)
  const [unpushing, setUnpushing] = useState(false)
  const [showPatientSearch, setShowPatientSearch] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('chief')

  const [chiefComplaint, setChiefComplaint] = useState('')
  const [vitals, setVitals] = useState<Vitals>({})
  const [medications, setMedications] = useState<Medication[]>([])
  const [pastMeds, setPastMeds] = useState<PastMedication[]>([])
  const [allergies, setAllergies] = useState<Allergy[]>([])
  const [diagnoses, setDiagnoses] = useState<Diagnosis[]>([])
  const [clinicalSummary, setClinicalSummary] = useState('')
  const [plan, setPlan] = useState('')
  const [transcript, setTranscript] = useState('')

  useEffect(() => {
    if (!id) return
    getEncounter(id)
      .then(data => {
        setRecord(data)
        setChiefComplaint(data.chief_complaint ?? '')
        setVitals(data.vitals ?? {})
        setMedications(data.medications)
        setPastMeds(data.past_medications)
        setAllergies(data.allergies)
        setDiagnoses(data.diagnoses)
        setClinicalSummary(data.clinical_summary ?? '')
        setPlan(data.plan ?? '')
        setTranscript(data.transcript ?? '')
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  async function handleSave() {
    if (!id) return
    setSaving(true)
    try {
      const updated = await updateEncounter(id, {
        chief_complaint: chiefComplaint,
        vitals,
        medications,
        past_medications: pastMeds,
        allergies,
        diagnoses,
        clinical_summary: clinicalSummary,
        plan,
        transcript,
      })
      setRecord(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleApprove() {
    if (!id || !record) return
    setApproving(true)
    try {
      await approveEncounter(id)
      const updated = await getEncounter(id)
      setRecord(updated)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setApproving(false)
    }
  }

  async function handleRevert() {
    if (!id || !record) return
    setReverting(true)
    try {
      await revertEncounter(id)
      const updated = await getEncounter(id)
      setRecord(updated)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setReverting(false)
    }
  }

  async function handleUnpush() {
    if (!id || !record) return
    setUnpushing(true)
    try {
      await unpushEncounter(id)
      const updated = await getEncounter(id)
      setRecord(updated)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setUnpushing(false)
    }
  }

  async function handlePushConfirm(patientUuid: string | null) {
    if (!id || !record) return
    
    setShowPatientSearch(false)
    setPushing(true)
    
    try {
      await pushToOpenMRS(id, patientUuid || '')
      const updated = await getEncounter(id)
      setRecord(updated)
      
      if (patientUuid === null) {
        alert(`Successfully created patient "${record.patient_name}" and pushed encounter to OpenMRS!`)
      } else {
        alert('Successfully pushed to OpenMRS!')
      }
    } catch (e: any) {
      setError(e.message)
      alert(`Failed to push: ${e.message}`)
    } finally {
      setPushing(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-screen gap-2 text-gray-500">
      <Loader2 size={18} className="animate-spin" /><span className="text-sm">Loading...</span>
    </div>
  )

  if (error || !record) return (
    <div className="p-8 text-red-400 text-sm">{error ?? 'Record not found.'}</div>
  )

  const { label, style } = statusMap[record.status]
  const canApprove = record.status === 'pending' && record.viewed
  const canRevert = record.status === 'approved'

  return (
    <div className="flex flex-col h-screen">
      <div className="px-8 py-5 border-b border-gray-800 flex items-center gap-4 shrink-0">
        <button onClick={() => navigate(-1)} className="p-1.5 text-gray-500 hover:text-white hover:bg-gray-800 rounded-lg transition-colors duration-150 cursor-pointer">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <h1 className="text-white text-lg font-semibold leading-tight">{record.patient_name}</h1>
          <p className="text-gray-500 text-xs mt-0.5">{record.patient_id}</p>
        </div>
        <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${style}`}>{label}</span>
        <button
          onClick={() => window.open(`http://localhost:8000/encounters/${id}/export/pdf`)}
          className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors duration-150 cursor-pointer"
        >
          <FileText size={14} />
          Export PDF
        </button>
        {readonly ? (
          <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-gray-700 text-gray-400 border border-gray-600">View Only</span>
        ) : (
          <>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors duration-150 cursor-pointer"
            >
              {saved ? <><Check size={14} /> Saved</> : saving ? <><Loader2 size={14} className="animate-spin" /> Saving…</> : 'Save Changes'}
            </button>
            
            {canRevert && (
              <button
                onClick={handleRevert}
                disabled={reverting}
                className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors duration-150 cursor-pointer"
              >
                {reverting ? <><Loader2 size={14} className="animate-spin" /> Reverting…</> : 'Unapprove'}
              </button>
            )}
            
            {record.status === 'pending' && (
              <button
                onClick={handleApprove}
                disabled={!canApprove || approving}
                title={!record.viewed ? 'Review the note before approving' : ''}
                className="flex items-center gap-2 bg-green-600 hover:bg-green-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors duration-150"
              >
                {!record.viewed && <Lock size={14} />}
                {approving ? <><Loader2 size={14} className="animate-spin" /> Approving…</> : 'Approve'}
              </button>
            )}
            
            {record.status === 'approved' && (
              <button
                onClick={() => setShowPatientSearch(true)}
                disabled={pushing}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors duration-150 cursor-pointer"
              >
                {pushing ? <><Loader2 size={14} className="animate-spin" /> Pushing…</> : <><Upload size={14} /> Push to OpenMRS</>}
              </button>
            )}
            
            {record.status === 'pushed' && (
              <button
                onClick={handleUnpush}
                disabled={unpushing}
                className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors duration-150 cursor-pointer"
              >
                {unpushing ? <><Loader2 size={14} className="animate-spin" /> Unpushing…</> : 'Unpush from OpenMRS'}
              </button>
            )}
          </>
        )}
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="w-56 shrink-0 border-r border-gray-800 p-5 flex flex-col gap-4 overflow-y-auto">
          <p className="text-gray-400 text-xs uppercase tracking-widest">Patient Details</p>
          {[
            { icon: User,     label: 'Full Name',  value: record.patient_name },
            { icon: User,     label: 'Patient ID', value: record.patient_id },
            { icon: Calendar, label: 'Date',       value: record.date },
            { icon: Clock,    label: 'Time',       value: record.time },
            { icon: Timer,    label: 'Duration',   value: record.duration ?? '—' },
          ].map(({ icon: Icon, label, value }) => (
            <div key={label} className="flex items-start gap-2.5">
              <Icon size={14} className="text-gray-600 mt-0.5 shrink-0" />
              <div>
                <p className="text-gray-500 text-xs mb-0.5">{label}</p>
                <p className="text-white text-xs font-mono">{value}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex items-center gap-1 px-6 pt-4 border-b border-gray-800 shrink-0 overflow-x-auto">
            {tabs.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors duration-150 cursor-pointer border-b-2 -mb-px whitespace-nowrap ${
                  activeTab === tab.id ? 'text-blue-400 border-blue-500' : 'text-gray-500 border-transparent hover:text-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-6">

            {activeTab === 'chief' && (
              <div className="max-w-2xl">
                <EditableField 
                  label="Chief Complaint" 
                  value={chiefComplaint} 
                  onChange={setChiefComplaint} 
                  multiline 
                  readonly={readonly}
                  placeholder="Patient's main reason for visit..."
                />
              </div>
            )}

            {activeTab === 'vitals' && (
              <div className="max-w-2xl grid grid-cols-2 gap-4">
                <EditableField label="Height (cm)" value={vitals.height_cm?.toString() ?? ''} readonly={readonly}
                  onChange={v => setVitals(prev => ({...prev, height_cm: v ? parseFloat(v) : undefined}))} />
                <EditableField label="Weight (kg)" value={vitals.weight_kg?.toString() ?? ''} readonly={readonly}
                  onChange={v => setVitals(prev => ({...prev, weight_kg: v ? parseFloat(v) : undefined}))} />
                <EditableField label="Temperature (°C)" value={vitals.temperature_c?.toString() ?? ''} readonly={readonly}
                  onChange={v => setVitals(prev => ({...prev, temperature_c: v ? parseFloat(v) : undefined}))} />
                <EditableField label="Pulse (bpm)" value={vitals.pulse?.toString() ?? ''} readonly={readonly}
                  onChange={v => setVitals(prev => ({...prev, pulse: v ? parseFloat(v) : undefined}))} />
                <EditableField label="BP Systolic (mmHg)" value={vitals.blood_pressure_systolic?.toString() ?? ''} readonly={readonly}
                  onChange={v => setVitals(prev => ({...prev, blood_pressure_systolic: v ? parseFloat(v) : undefined}))} />
                <EditableField label="BP Diastolic (mmHg)" value={vitals.blood_pressure_diastolic?.toString() ?? ''} readonly={readonly}
                  onChange={v => setVitals(prev => ({...prev, blood_pressure_diastolic: v ? parseFloat(v) : undefined}))} />
                <EditableField label="SpO₂ (%)" value={vitals.spo2_pct?.toString() ?? ''} readonly={readonly}
                  onChange={v => setVitals(prev => ({...prev, spo2_pct: v ? parseFloat(v) : undefined}))} />
                <EditableField label="Resp Rate (breaths/min)" value={vitals.resp_rate?.toString() ?? ''} readonly={readonly}
                  onChange={v => setVitals(prev => ({...prev, resp_rate: v ? parseFloat(v) : undefined}))} />
              </div>
            )}

            {activeTab === 'diagnoses' && (
              <div className="max-w-2xl flex flex-col gap-5">
                {diagnoses.map((dx, i) => (
                  <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-3">
                    <p className="text-white text-sm font-medium">Diagnosis {i + 1}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <EditableField label="ICD-10 Code" value={dx.icd10_code ?? ''} readonly={readonly} placeholder="E.g. J06.9"
                        onChange={v => setDiagnoses(ds => ds.map((d, j) => j===i ? {...d, icd10_code: v} : d))} />
                      <EditableField label="Status" value={dx.status ?? ''} readonly={readonly} placeholder="Presumed / Confirmed / Ruled Out"
                        onChange={v => setDiagnoses(ds => ds.map((d, j) => j===i ? {...d, status: v} : d))} />
                      <div className="col-span-2">
                        <EditableField label="Description" value={dx.description} readonly={readonly} placeholder="Diagnosis description..."
                          onChange={v => setDiagnoses(ds => ds.map((d, j) => j===i ? {...d, description: v} : d))} />
                      </div>
                    </div>
                    {!readonly && (
                      <button onClick={() => setDiagnoses(ds => ds.filter((_, j) => j !== i))}
                        className="text-red-400 hover:text-red-300 text-xs font-medium text-left cursor-pointer transition-colors duration-150">
                        Remove
                      </button>
                    )}
                  </div>
                ))}
                {!readonly && (
                  <button onClick={() => setDiagnoses(ds => [...ds, { icd10_code: '', description: '', status: '' }])}
                    className="text-blue-400 hover:text-blue-300 text-sm font-medium text-left cursor-pointer transition-colors duration-150">
                    + Add Diagnosis
                  </button>
                )}
              </div>
            )}

            {activeTab === 'medications' && (
              <div className="max-w-2xl flex flex-col gap-5">
                {medications.map((med, i) => (
                  <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-3">
                    <p className="text-white text-sm font-medium">Medication {i + 1}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <EditableField label="Drug Name" value={med.name} readonly={readonly} placeholder="E.g. Lisinopril"
                        onChange={v => setMedications(ms => ms.map((m, j) => j===i ? {...m, name: v} : m))} />
                      <EditableField label="Dose" value={med.dose ?? ''} readonly={readonly} placeholder="E.g. 10 mg"
                        onChange={v => setMedications(ms => ms.map((m, j) => j===i ? {...m, dose: v} : m))} />
                      <EditableField label="Route" value={med.route ?? ''} readonly={readonly} placeholder="E.g. Oral"
                        onChange={v => setMedications(ms => ms.map((m, j) => j===i ? {...m, route: v} : m))} />
                      <EditableField label="Frequency" value={med.frequency ?? ''} readonly={readonly} placeholder="E.g. Daily"
                        onChange={v => setMedications(ms => ms.map((m, j) => j===i ? {...m, frequency: v} : m))} />
                      <EditableField label="Start Date" value={med.start_date ?? ''} readonly={readonly} placeholder="YYYY-MM-DD"
                        onChange={v => setMedications(ms => ms.map((m, j) => j===i ? {...m, start_date: v} : m))} />
                    </div>
                    {!readonly && (
                      <button onClick={() => setMedications(ms => ms.filter((_, j) => j !== i))}
                        className="text-red-400 hover:text-red-300 text-xs font-medium text-left cursor-pointer transition-colors duration-150">
                        Remove
                      </button>
                    )}
                  </div>
                ))}
                {!readonly && (
                  <button onClick={() => setMedications(ms => [...ms, { name: '', dose: '', route: '', frequency: '', start_date: '' }])}
                    className="text-blue-400 hover:text-blue-300 text-sm font-medium text-left cursor-pointer transition-colors duration-150">
                    + Add Medication
                  </button>
                )}
              </div>
            )}

            {activeTab === 'past_meds' && (
              <div className="max-w-2xl flex flex-col gap-5">
                {pastMeds.map((pm, i) => (
                  <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-3">
                    <p className="text-white text-sm font-medium">Past Medication {i + 1}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <EditableField label="Drug Name" value={pm.name} readonly={readonly} placeholder="E.g. Aspirin"
                        onChange={v => setPastMeds(pms => pms.map((m, j) => j===i ? {...m, name: v} : m))} />
                      <EditableField label="Dose" value={pm.dose ?? ''} readonly={readonly} placeholder="E.g. 81 mg"
                        onChange={v => setPastMeds(pms => pms.map((m, j) => j===i ? {...m, dose: v} : m))} />
                      <EditableField label="Route" value={pm.route ?? ''} readonly={readonly} placeholder="E.g. Oral"
                        onChange={v => setPastMeds(pms => pms.map((m, j) => j===i ? {...m, route: v} : m))} />
                      <EditableField label="Frequency" value={pm.frequency ?? ''} readonly={readonly} placeholder="E.g. Daily"
                        onChange={v => setPastMeds(pms => pms.map((m, j) => j===i ? {...m, frequency: v} : m))} />
                      <EditableField label="Start Date" value={pm.start_date ?? ''} readonly={readonly} placeholder="YYYY-MM-DD"
                        onChange={v => setPastMeds(pms => pms.map((m, j) => j===i ? {...m, start_date: v} : m))} />
                      <EditableField label="End Date" value={pm.end_date ?? ''} readonly={readonly} placeholder="YYYY-MM-DD"
                        onChange={v => setPastMeds(pms => pms.map((m, j) => j===i ? {...m, end_date: v} : m))} />
                      <div className="col-span-2">
                        <EditableField label="Reason Discontinued" value={pm.reason ?? ''} readonly={readonly} placeholder="Why was this stopped?"
                          onChange={v => setPastMeds(pms => pms.map((m, j) => j===i ? {...m, reason: v} : m))} />
                      </div>
                    </div>
                    {!readonly && (
                      <button onClick={() => setPastMeds(pms => pms.filter((_, j) => j !== i))}
                        className="text-red-400 hover:text-red-300 text-xs font-medium text-left cursor-pointer transition-colors duration-150">
                        Remove
                      </button>
                    )}
                  </div>
                ))}
                {!readonly && (
                  <button onClick={() => setPastMeds(pms => [...pms, { name: '', dose: '', route: '', frequency: '', start_date: '', end_date: '', reason: '' }])}
                    className="text-blue-400 hover:text-blue-300 text-sm font-medium text-left cursor-pointer transition-colors duration-150">
                    + Add Past Medication
                  </button>
                )}
              </div>
            )}

            {activeTab === 'allergies' && (
              <div className="max-w-2xl flex flex-col gap-5">
                {allergies.map((a, i) => (
                  <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-3">
                    <p className="text-white text-sm font-medium">Allergy {i + 1}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <EditableField label="Allergen" value={a.allergen} readonly={readonly} placeholder="E.g. Penicillin"
                        onChange={v => setAllergies(as => as.map((x, j) => j===i ? {...x, allergen: v} : x))} />
                      <EditableField label="Reaction" value={a.reaction ?? ''} readonly={readonly} placeholder="E.g. Rash"
                        onChange={v => setAllergies(as => as.map((x, j) => j===i ? {...x, reaction: v} : x))} />
                      <EditableField label="Severity" value={a.severity ?? ''} readonly={readonly} placeholder="Mild / Moderate / Severe"
                        onChange={v => setAllergies(as => as.map((x, j) => j===i ? {...x, severity: v} : x))} />
                    </div>
                    {!readonly && (
                      <button onClick={() => setAllergies(as => as.filter((_, j) => j !== i))}
                        className="text-red-400 hover:text-red-300 text-xs font-medium text-left cursor-pointer transition-colors duration-150">
                        Remove
                      </button>
                    )}
                  </div>
                ))}
                {!readonly && (
                  <button onClick={() => setAllergies(as => [...as, { allergen: '', reaction: '', severity: '' }])}
                    className="text-blue-400 hover:text-blue-300 text-sm font-medium text-left cursor-pointer transition-colors duration-150">
                    + Add Allergy
                  </button>
                )}
              </div>
            )}


            {activeTab === 'summary' && (
              <div className="max-w-2xl">
                <EditableField 
                  label="Clinical Summary / Assessment" 
                  value={clinicalSummary} 
                  onChange={setClinicalSummary} 
                  multiline 
                  readonly={readonly}
                  placeholder="Overall clinical assessment..."
                />
              </div>
            )}

            {activeTab === 'plan' && (
              <div className="max-w-2xl">
                <EditableField 
                  label="Treatment Plan" 
                  value={plan} 
                  onChange={setPlan} 
                  multiline 
                  readonly={readonly}
                  placeholder="Treatment plan and follow-up..."
                />
              </div>
            )}

            {activeTab === 'transcript' && (
              <div className="max-w-2xl flex flex-col gap-1.5">
                <label className="text-gray-500 text-xs font-medium uppercase tracking-wider">Raw Transcript</label>
                <textarea value={transcript} onChange={e => !readonly && setTranscript(e.target.value)} readOnly={readonly} rows={20}
                  placeholder="Doctor-patient conversation transcript..."
                  className={`text-sm rounded-lg px-4 py-3 outline-none transition-colors duration-150 resize-none leading-loose font-mono ${
                    readonly ? 'bg-transparent border border-gray-800 text-gray-400 cursor-default' : 'bg-gray-800 border border-gray-700 text-gray-200 placeholder:text-gray-600 focus:border-blue-600'
                  }`}
                />
              </div>
            )}

          </div>
        </div>
      </div>
      
      {showPatientSearch && record && (
        <PatientSearchModal 
          record={record} 
          onConfirm={handlePushConfirm} 
          onCancel={() => setShowPatientSearch(false)} 
        />
      )}
    </div>
  )
}
