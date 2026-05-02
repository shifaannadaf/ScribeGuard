import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Clock, CheckCircle2, Layers, Mic, Upload, Square, X, Loader2, Check, Search } from 'lucide-react'
import { getStats, createEncounter, transcribeAudio, generateNote, formatEncounter, getPatientStatus, type Stats } from '../api/encounters'
import { searchPatients, type OpenMRSPatient } from '../api/openmrs'

type RecordState = 'idle' | 'setup' | 'recording' | 'processing'
type Step = { label: string; status: 'pending' | 'active' | 'done' }

const PREVIEW_LINES = [
  { speaker: 'Doctor',  text: 'How long have you been experiencing this pain?' },
  { speaker: 'Patient', text: 'It started about three days ago, mostly in the lower back.' },
  { speaker: 'Doctor',  text: 'Does it radiate down your leg at all?' },
  { speaker: 'Patient', text: 'Sometimes, yes — on the right side.' },
]

function fmtTime(s: number) {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats]             = useState<Stats | null>(null)
  const [recState, setRecState]       = useState<RecordState>('idle')
  const [patientName,    setPatientName]    = useState('')
  const [patientId,      setPatientId]      = useState('')
  const [elapsed,        setElapsed]        = useState(0)
  const [steps,          setSteps]          = useState<Step[]>([])
  const [error,          setError]          = useState<string | null>(null)
  const [omrsQuery,      setOmrsQuery]      = useState('')
  const [omrsPatient,    setOmrsPatient]    = useState<OpenMRSPatient | null>(null)
  const [omrsResults,    setOmrsResults]    = useState<OpenMRSPatient[]>([])
  const [omrsSearching,  setOmrsSearching]  = useState(false)
  const [omrsError,      setOmrsError]      = useState<string | null>(null)
  const [patientType,    setPatientType]    = useState<'new' | 'returning' | null>(null)
  const [encounterCount, setEncounterCount] = useState(0)
  const [lastVisit,      setLastVisit]      = useState<string | null>(null)
  const [importedFile,   setImportedFile]   = useState<{ name: string; content: string } | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef        = useRef<Blob[]>([])
  const timerRef         = useRef<ReturnType<typeof setInterval> | null>(null)
  const streamRef        = useRef<MediaStream | null>(null)

  useEffect(() => { getStats().then(setStats).catch(() => {}) }, [])

  async function startRecording() {
    if (!patientName.trim() || !patientId.trim()) return
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      chunksRef.current = []

      const mr = new MediaRecorder(stream)
      mediaRecorderRef.current = mr
      mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      mr.start(250)

      setElapsed(0)
      timerRef.current = setInterval(() => setElapsed(s => s + 1), 1000)
      setRecState('recording')
    } catch {
      setError('Microphone access denied. Please allow microphone permissions and try again.')
    }
  }

  function updateStep(i: number, s: Step['status']) {
    setSteps(prev => prev.map((step, idx) => idx === i ? { ...step, status: s } : step))
  }

  async function stopRecording() {
    const mr = mediaRecorderRef.current
    if (!mr) return
    timerRef.current && clearInterval(timerRef.current)
    streamRef.current?.getTracks().forEach(t => t.stop())

    setSteps([
      { label: 'Creating encounter',   status: 'active'  },
      { label: 'Transcribing audio',   status: 'pending' },
      { label: 'Generating SOAP note', status: 'pending' },
    ])
    setRecState('processing')

    mr.onstop = async () => {
      try {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })

        const enc = await createEncounter(
          patientName.trim(),
          patientId.trim(),
          patientType ?? 'new',
          omrsPatient?.uuid,
        )
        updateStep(0, 'done'); updateStep(1, 'active')

        await transcribeAudio(enc.id, blob)
        updateStep(1, 'done'); updateStep(2, 'active')

        await generateNote(enc.id)
        updateStep(2, 'done')

        getStats().then(setStats).catch(() => {})
        setTimeout(() => navigate(`/notes/${enc.id}`), 600)
      } catch (e: any) {
        setError(e.message ?? 'Something went wrong. Please try again.')
        setRecState('idle')
        setSteps([])
      }
    }
    mr.stop()
  }

  async function handleFileImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    // Reset file input
    e.target.value = ''

    if (!file.name.endsWith('.txt')) {
      setError('Only .txt files are supported for import')
      setTimeout(() => setError(null), 3000)
      return
    }

    try {
      const content = await file.text()
      setImportedFile({ name: file.name, content })
      setRecState('setup')
      setError(null)
    } catch (e: any) {
      setError('Failed to read file')
      setTimeout(() => setError(null), 3000)
    }
  }

  async function handleImportSubmit() {
    if (!patientName.trim() || !patientId.trim() || !importedFile) return
    setError(null)

    setSteps([
      { label: 'Creating encounter',   status: 'active'  },
      { label: 'Processing transcript', status: 'pending' },
      { label: 'Generating SOAP note', status: 'pending' },
    ])
    setRecState('processing')

    try {
      const enc = await createEncounter(
        patientName.trim(),
        patientId.trim(),
        patientType ?? 'new',
        omrsPatient?.uuid,
      )
      updateStep(0, 'done'); updateStep(1, 'active')

      // Update encounter with imported transcript
      await fetch(`http://localhost:8000/encounters/${enc.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript: importedFile.content })
      })

      // Format the transcript
      await formatEncounter(enc.id)
      updateStep(1, 'done'); updateStep(2, 'active')

      await generateNote(enc.id)
      updateStep(2, 'done')

      getStats().then(setStats).catch(() => {})
      setTimeout(() => navigate(`/notes/${enc.id}`), 600)
    } catch (e: any) {
      setError(e.message ?? 'Failed to import transcript')
      setRecState('idle')
      setSteps([])
    }
  }

  async function searchOmrs() {
    if (!omrsQuery.trim()) return
    setOmrsSearching(true)
    setOmrsError(null)
    setOmrsPatient(null)
    setOmrsResults([])
    try {
      const results = await searchPatients(omrsQuery.trim())
      if (results.length === 0) {
        setOmrsError('No patients found.')
      } else if (results.length === 1) {
        selectOmrsPatient(results[0])
      } else {
        setOmrsResults(results)
      }
    } catch {
      setOmrsError('Could not reach OpenMRS.')
    } finally {
      setOmrsSearching(false)
    }
  }

  async function selectOmrsPatient(p: OpenMRSPatient) {
    setOmrsPatient(p)
    setOmrsResults([])
    setPatientName(p.name)
    setPatientId(p.identifier)
    try {
      const s = await getPatientStatus(p.identifier)
      setPatientType(s.patient_type)
      setEncounterCount(s.encounter_count)
      setLastVisit(s.last_visit)
    } catch {
      setPatientType('returning') // found in OpenMRS = known patient
    }
  }

  function cancelSetup() {
    setRecState('idle')
    setPatientName('')
    setPatientId('')
    setOmrsQuery('')
    setOmrsPatient(null)
    setOmrsResults([])
    setOmrsError(null)
    setPatientType(null)
    setEncounterCount(0)
    setLastVisit(null)
    setImportedFile(null)
    setError(null)
    setError(null)
  }

  const cards = [
    { label: 'Notes Today',       value: stats?.notes_today       ?? '—', icon: FileText,    color: 'text-blue-400',   bg: 'bg-blue-500/10'   },
    { label: 'Pending Review',    value: stats?.pending_review    ?? '—', icon: Clock,       color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
    { label: 'Pushed to OpenMRS', value: stats?.pushed_to_openmrs ?? '—', icon: CheckCircle2,color: 'text-green-400',  bg: 'bg-green-500/10'  },
    { label: 'Total Transcripts', value: stats?.total_transcripts ?? '—', icon: Layers,      color: 'text-purple-400', bg: 'bg-purple-500/10' },
  ]

  return (
    <div className="flex flex-col h-screen">

      <div className="p-8 pb-6 shrink-0">
        <h1 className="text-white text-2xl font-semibold mb-1">Dashboard</h1>
        <p className="text-gray-500 text-sm mb-6">Welcome back. Here's your activity at a glance.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {cards.map(({ label, value, icon: Icon, color, bg }) => (
            <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-center gap-4">
              <div className={`${bg} rounded-lg p-3 shrink-0`}><Icon size={22} className={color} /></div>
              <div>
                <p className="text-gray-400 text-sm">{label}</p>
                <p className="text-white text-2xl font-bold mt-0.5">{value}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 mx-8 mb-8 bg-gray-900 border border-gray-800 rounded-xl flex flex-col overflow-hidden">

        {/* Controls */}
        <div className="flex flex-col items-center justify-center gap-4 py-8 border-b border-gray-800">

          {recState === 'idle' && (
            <div className="flex items-center gap-12">
              <button onClick={() => setRecState('setup')} className="flex flex-col items-center gap-2 group cursor-pointer">
                <Mic size={36} className="text-blue-400 group-hover:text-blue-300 transition-colors duration-150" />
                <span className="text-gray-400 group-hover:text-gray-200 text-xs transition-colors duration-150">Record</span>
              </button>
              <label className="flex flex-col items-center gap-2 group cursor-pointer">
  <Upload size={36} className="text-gray-500 group-hover:text-gray-300 transition-colors duration-150" />
  <span className="text-gray-500 group-hover:text-gray-300 text-xs transition-colors duration-150">
    Import
  </span>

  <input
    type="file"
    accept=".txt"
    className="hidden"
    onChange={handleFileImport}
  />
</label>
 
            </div>
          )}

          {recState === 'setup' && (
            <div className="w-full max-w-sm px-4 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <p className="text-white text-sm font-semibold">New Recording</p>
                <button onClick={cancelSetup} className="text-gray-600 hover:text-white transition-colors cursor-pointer"><X size={16} /></button>
              </div>

              {/* OpenMRS search */}
              <div className="flex flex-col gap-1.5">
                <label className="text-gray-500 text-xs uppercase tracking-wider">Search OpenMRS</label>
                <div className="flex gap-2">
                  <input
                    type="text" value={omrsQuery}
                    onChange={e => { setOmrsQuery(e.target.value); setOmrsError(null); setOmrsResults([]); setOmrsPatient(null) }}
                    onKeyDown={e => e.key === 'Enter' && searchOmrs()}
                    placeholder="Name or ID (e.g. Atharv or 10001PE)" autoFocus
                    className="flex-1 bg-gray-800 border border-gray-700 text-gray-200 placeholder-gray-600 text-sm rounded-lg px-3 py-2.5 outline-none focus:border-blue-600 transition-colors duration-150"
                  />
                  <button onClick={searchOmrs} disabled={omrsSearching || !omrsQuery.trim()}
                    className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white px-3 rounded-lg transition-colors duration-150 cursor-pointer">
                    {omrsSearching ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
                  </button>
                </div>
                {omrsError && <p className="text-red-400 text-xs">{omrsError}</p>}
              </div>

              {/* Multiple results dropdown */}
              {omrsResults.length > 0 && (
                <div className="flex flex-col gap-1">
                  {omrsResults.map(p => (
                    <button key={p.uuid} onClick={() => selectOmrsPatient(p)}
                      className="text-left bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg px-3 py-2 transition-colors cursor-pointer">
                      <p className="text-gray-200 text-sm font-medium">{p.name}</p>
                      <p className="text-gray-500 text-xs">{p.identifier} · {p.gender?.toUpperCase() ?? '—'} · {p.birthdate ?? '—'}</p>
                    </button>
                  ))}
                </div>
              )}

              {/* Patient confirmed + type badge */}
              {omrsPatient && (
                <div className="flex flex-col gap-2">
                  <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-3 py-2.5 flex items-center gap-3">
                    <CheckCircle2 size={16} className="text-green-400 shrink-0" />
                    <div className="min-w-0">
                      <p className="text-green-300 text-sm font-medium truncate">{omrsPatient.name}</p>
                      <p className="text-green-500 text-xs">{omrsPatient.identifier} · {omrsPatient.gender?.toUpperCase() ?? '—'} · {omrsPatient.birthdate ?? '—'}</p>
                    </div>
                  </div>
                  {patientType && (
                    <div className={`rounded-lg px-3 py-2 flex items-center gap-2 ${
                      patientType === 'returning'
                        ? 'bg-blue-500/10 border border-blue-500/20'
                        : 'bg-purple-500/10 border border-purple-500/20'
                    }`}>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                        patientType === 'returning'
                          ? 'bg-blue-500/20 text-blue-300'
                          : 'bg-purple-500/20 text-purple-300'
                      }`}>
                        {patientType === 'returning' ? 'Returning Patient' : 'New Patient'}
                      </span>
                      {patientType === 'returning' && encounterCount > 0 && (
                        <span className="text-gray-500 text-xs">
                          {encounterCount} prior visit{encounterCount !== 1 ? 's' : ''} in ScribeGuard
                          {lastVisit && ` · last ${new Date(lastVisit).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`}
                        </span>
                      )}
                      {patientType === 'returning' && encounterCount === 0 && (
                        <span className="text-gray-500 text-xs">Registered in OpenMRS</span>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="border-t border-gray-800" />

              {/* Manual fields */}
              <div className="flex flex-col gap-3">
                {importedFile && (
                  <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg px-3 py-2">
                    <div className="flex items-center gap-2">
                      <FileText size={14} className="text-blue-400" />
                      <span className="text-blue-300 text-xs font-medium">{importedFile.name}</span>
                    </div>
                  </div>
                )}
                <div className="flex flex-col gap-1.5">
                  <label className="text-gray-500 text-xs uppercase tracking-wider">Patient Name</label>
                  <input type="text" value={patientName} onChange={e => setPatientName(e.target.value)}
                    placeholder="e.g. John Doe"
                    className="bg-gray-800 border border-gray-700 text-gray-200 placeholder-gray-600 text-sm rounded-lg px-3 py-2.5 outline-none focus:border-blue-600 transition-colors duration-150" />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-gray-500 text-xs uppercase tracking-wider">Patient ID</label>
                  <input type="text" value={patientId} onChange={e => setPatientId(e.target.value)}
                    placeholder="e.g. P-00123"
                    onKeyDown={e => e.key === 'Enter' && (importedFile ? handleImportSubmit() : startRecording())}
                    className="bg-gray-800 border border-gray-700 text-gray-200 placeholder-gray-600 text-sm rounded-lg px-3 py-2.5 outline-none focus:border-blue-600 transition-colors duration-150" />
                </div>
              </div>

              {error && <p className="text-red-400 text-xs">{error}</p>}
              <button 
                onClick={importedFile ? handleImportSubmit : startRecording} 
                disabled={!patientName.trim() || !patientId.trim()}
                className="flex items-center justify-center gap-2 bg-red-600 hover:bg-red-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors duration-150 cursor-pointer">
                {importedFile ? (
                  <>
                    <Upload size={15} /> Import & Process
                  </>
                ) : (
                  <>
                    <Mic size={15} /> Start Recording
                  </>
                )}
              </button>
            </div>
          )}

          {recState === 'recording' && (
            <div className="flex flex-col items-center gap-3">
              <div className="flex items-center gap-3">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                <span className="text-white font-mono text-lg font-semibold">{fmtTime(elapsed)}</span>
                <span className="text-gray-500 text-sm">Recording…</span>
              </div>
              <p className="text-gray-600 text-xs">{patientName} · {patientId}</p>
              <button onClick={stopRecording}
                className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors duration-150 cursor-pointer mt-1">
                <Square size={14} className="fill-current" /> Stop Recording
              </button>
            </div>
          )}

          {recState === 'processing' && (
            <div className="flex flex-col gap-3 w-64">
              {steps.map((step, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="w-5 h-5 shrink-0 flex items-center justify-center">
                    {step.status === 'done'    && <Check size={16} className="text-green-400" />}
                    {step.status === 'active'  && <Loader2 size={16} className="text-blue-400 animate-spin" />}
                    {step.status === 'pending' && <div className="w-1.5 h-1.5 rounded-full bg-gray-700" />}
                  </div>
                  <span className={`text-sm ${step.status === 'active' ? 'text-white' : step.status === 'done' ? 'text-gray-400' : 'text-gray-600'}`}>
                    {step.label}
                  </span>
                </div>
              ))}
            </div>
          )}

        </div>

        {/* Preview panel */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center gap-2 mb-5">
            <span className={`w-2 h-2 rounded-full ${recState === 'recording' ? 'bg-red-500 animate-pulse' : 'bg-gray-700'}`} />
            <span className="text-gray-400 text-xs uppercase tracking-widest">
              {recState === 'recording' ? 'Recording in progress' : 'Transcription Preview'}
            </span>
          </div>

          {recState === 'recording' ? (
            <div className="flex flex-col items-center justify-center h-32 gap-3">
              <div className="flex items-end gap-1 h-8">
                {[3,5,8,5,9,4,7,5,3,6,8,4].map((h, i) => (
                  <div key={i} className="w-1 bg-blue-500/60 rounded-full animate-pulse"
                    style={{ height: `${h * 4}px`, animationDelay: `${i * 80}ms` }} />
                ))}
              </div>
              <p className="text-gray-500 text-xs">Transcript will appear after processing</p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {PREVIEW_LINES.map(({ speaker, text }, i) => (
                <div key={i} className="flex gap-3">
                  <span className={`text-xs font-semibold w-14 shrink-0 pt-0.5 ${speaker === 'Doctor' ? 'text-blue-400' : 'text-gray-500'}`}>
                    {speaker}
                  </span>
                  <p className="text-gray-300 text-sm leading-relaxed">{text}</p>
                </div>
              ))}
              <div className="flex gap-3">
                <span className="text-xs font-semibold w-14 shrink-0 pt-0.5 text-blue-400">Doctor</span>
                <p className="text-gray-500 text-sm italic">Listening<span className="animate-pulse">...</span></p>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
