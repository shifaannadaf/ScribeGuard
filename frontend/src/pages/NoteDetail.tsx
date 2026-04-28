import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, User, Calendar, Clock, Timer, Loader2, Check, FileText } from 'lucide-react'
import { getEncounter, updateEncounter, type EncounterDetail, type Medication, type Allergy, type Diagnosis } from '../api/encounters'
type Tab = 'transcription' | 'medications' | 'allergies' | 'diagnoses'

const tabs: { id: Tab; label: string }[] = [
  { id: 'transcription', label: 'Transcription' },
  { id: 'medications',   label: 'Medications' },
  { id: 'allergies',     label: 'Allergies' },
  { id: 'diagnoses',     label: 'Diagnoses' },
]

const statusMap = {
  pending:  { label: 'Pending Review', style: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' },
  approved: { label: 'Approved',       style: 'bg-green-500/10 text-green-400 border border-green-500/20' },
  pushed:   { label: 'In OpenMRS',     style: 'bg-blue-500/10 text-blue-400 border border-blue-500/20' },
}

function EditableField({ label, value, onChange, multiline = false, readonly = false }: {
  label: string; value: string; onChange: (v: string) => void; multiline?: boolean; readonly?: boolean
}) {
  const base = 'text-sm rounded-lg px-3 py-2.5 outline-none transition-colors duration-150'
  const edit = 'bg-gray-800 border border-gray-700 text-gray-200 focus:border-blue-600'
  const read = 'bg-transparent border border-gray-800 text-gray-400 cursor-default select-text'
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-gray-500 text-xs font-medium uppercase tracking-wider">{label}</label>
      {multiline ? (
        <textarea value={value} onChange={e => !readonly && onChange(e.target.value)} readOnly={readonly} rows={3}
          className={`${base} ${readonly ? read : edit} resize-none leading-relaxed`} />
      ) : (
        <input type="text" value={value} onChange={e => !readonly && onChange(e.target.value)} readOnly={readonly}
          className={`${base} ${readonly ? read : edit}`} />
      )}
    </div>
  )
}

export default function NoteDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const readonly = searchParams.get('mode') === 'view'

  const [record, setRecord]           = useState<EncounterDetail | null>(null)
  const [loading, setLoading]         = useState(true)
  const [saving, setSaving]           = useState(false)
  const [saved, setSaved]             = useState(false)
  const [error, setError]             = useState<string | null>(null)
  const [activeTab, setActiveTab]     = useState<Tab>('transcription')
  const [transcript, setTranscript]   = useState('')
  const [medications, setMedications] = useState<Medication[]>([])
  const [allergies, setAllergies]     = useState<Allergy[]>([])
  const [diagnoses, setDiagnoses]     = useState<Diagnosis[]>([])

  useEffect(() => {
    if (!id) return
    getEncounter(id)
      .then(data => {
        setRecord(data)
        setTranscript(data.transcript ?? '')
        setMedications(data.medications)
        setAllergies(data.allergies)
        setDiagnoses(data.diagnoses)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  async function handleSave() {
    if (!id) return
    setSaving(true)
    try {
      await updateEncounter(id, { transcript, medications, allergies, diagnoses })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSaving(false)
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
        {readonly
          ? <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-gray-700 text-gray-400 border border-gray-600">View Only</span>
          : (
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors duration-150 cursor-pointer"
            >
              {saved ? <><Check size={14} /> Saved</> : saving ? <><Loader2 size={14} className="animate-spin" /> Saving…</> : 'Save Changes'}
            </button>
          )
        }
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
          <div className="flex items-center gap-1 px-6 pt-4 border-b border-gray-800 shrink-0">
            {tabs.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors duration-150 cursor-pointer border-b-2 -mb-px ${
                  activeTab === tab.id ? 'text-blue-400 border-blue-500' : 'text-gray-500 border-transparent hover:text-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-6">

            {activeTab === 'transcription' && (
              <div className="max-w-2xl flex flex-col gap-1.5">
                <label className="text-gray-500 text-xs font-medium uppercase tracking-wider">Raw Transcript</label>
                <textarea value={transcript} onChange={e => !readonly && setTranscript(e.target.value)} readOnly={readonly} rows={20}
                  className={`text-sm rounded-lg px-4 py-3 outline-none transition-colors duration-150 resize-none leading-loose font-mono ${
                    readonly ? 'bg-transparent border border-gray-800 text-gray-400 cursor-default' : 'bg-gray-800 border border-gray-700 text-gray-200 focus:border-blue-600'
                  }`}
                />
              </div>
            )}

            {activeTab === 'medications' && (
              <div className="max-w-2xl flex flex-col gap-5">
                {medications.map((med, i) => (
                  <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-3">
                    <p className="text-white text-sm font-medium">Medication {i + 1}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <EditableField label="Drug Name"  value={med.name}         readonly={readonly} onChange={v => setMedications(ms => ms.map((m, j) => j===i ? {...m, name: v} : m))} />
                      <EditableField label="Dose"       value={med.dose ?? ''}   readonly={readonly} onChange={v => setMedications(ms => ms.map((m, j) => j===i ? {...m, dose: v} : m))} />
                      <EditableField label="Route"      value={med.route ?? ''}  readonly={readonly} onChange={v => setMedications(ms => ms.map((m, j) => j===i ? {...m, route: v} : m))} />
                      <EditableField label="Frequency"  value={med.frequency ?? ''} readonly={readonly} onChange={v => setMedications(ms => ms.map((m, j) => j===i ? {...m, frequency: v} : m))} />
                      <EditableField label="Start Date" value={med.start_date ?? ''} readonly={readonly} onChange={v => setMedications(ms => ms.map((m, j) => j===i ? {...m, start_date: v} : m))} />
                    </div>
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

            {activeTab === 'allergies' && (
              <div className="max-w-2xl flex flex-col gap-5">
                {allergies.map((a, i) => (
                  <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-3">
                    <p className="text-white text-sm font-medium">Allergy {i + 1}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <EditableField label="Allergen" value={a.allergen}        readonly={readonly} onChange={v => setAllergies(as => as.map((x, j) => j===i ? {...x, allergen: v} : x))} />
                      <EditableField label="Reaction" value={a.reaction ?? ''}  readonly={readonly} onChange={v => setAllergies(as => as.map((x, j) => j===i ? {...x, reaction: v} : x))} />
                      <EditableField label="Severity" value={a.severity ?? ''}  readonly={readonly} onChange={v => setAllergies(as => as.map((x, j) => j===i ? {...x, severity: v} : x))} />
                    </div>
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

            {activeTab === 'diagnoses' && (
              <div className="max-w-2xl flex flex-col gap-5">
                {diagnoses.map((dx, i) => (
                  <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-3">
                    <p className="text-white text-sm font-medium">Diagnosis {i + 1}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <EditableField label="ICD-10 Code"  value={dx.icd10_code ?? ''}  readonly={readonly} onChange={v => setDiagnoses(ds => ds.map((d, j) => j===i ? {...d, icd10_code: v} : d))} />
                      <EditableField label="Status"       value={dx.status ?? ''}       readonly={readonly} onChange={v => setDiagnoses(ds => ds.map((d, j) => j===i ? {...d, status: v} : d))} />
                      <div className="col-span-2">
                        <EditableField label="Description" value={dx.description} readonly={readonly} onChange={v => setDiagnoses(ds => ds.map((d, j) => j===i ? {...d, description: v} : d))} />
                      </div>
                    </div>
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

          </div>
        </div>
      </div>
    </div>
  )
}
