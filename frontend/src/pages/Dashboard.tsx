import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Clock, CheckCircle2, Layers, Mic, Upload, Square, X, Loader2, Check } from 'lucide-react'
import { getStats, createEncounter, transcribeAudio, generateNote, type Stats } from '../api/encounters'
import './Dashboard.css'

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
  const [patientName, setPatientName] = useState('')
  const [patientId,   setPatientId]   = useState('')
  const [elapsed, setElapsed]         = useState(0)
  const [steps,   setSteps]           = useState<Step[]>([])
  const [error,   setError]           = useState<string | null>(null)

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

        const enc = await createEncounter(patientName.trim(), patientId.trim())
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

  function cancelSetup() {
    setRecState('idle')
    setPatientName('')
    setPatientId('')
    setError(null)
  }

  const cards = [
    { label: 'Notes Today',       value: stats?.notes_today       ?? '—', icon: FileText,    colorClass: 'stat-blue'   },
    { label: 'Pending Review',    value: stats?.pending_review    ?? '—', icon: Clock,       colorClass: 'stat-yellow' },
    { label: 'Pushed to OpenMRS', value: stats?.pushed_to_openmrs ?? '—', icon: CheckCircle2,colorClass: 'stat-green'  },
    { label: 'Total Transcripts', value: stats?.total_transcripts ?? '—', icon: Layers,      colorClass: 'stat-purple' },
  ]

  return (
    <div className="dashboard-container">

      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 className="page-title">Dashboard</h1>
            <p className="page-subtitle">Welcome back. Here's your activity at a glance.</p>
          </div>
          <button 
            onClick={() => navigate('/notes/demo-123')} 
            className="btn btn-primary"
            style={{ background: 'var(--success)' }}
          >
            <FileText size={16} /> View Demo SOAP Encounter
          </button>
        </div>
        <div className="dashboard-stats-grid" style={{ marginTop: '1.5rem' }}>
          {cards.map(({ label, value, icon: Icon, colorClass }) => (
            <div key={label} className={`glass-card stat-card ${colorClass}`}>
              <div className="stat-icon-wrapper"><Icon size={22} /></div>
              <div>
                <p className="stat-label">{label}</p>
                <p className="stat-value">{value}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="dashboard-main-area glass-panel">

        {/* Controls */}
        <div className="recording-controls">

          {recState === 'idle' && (
            <div className="action-buttons-row">
              <button onClick={() => setRecState('setup')} className="action-button primary">
                <Mic size={36} className="icon" />
                <span className="label">Record</span>
              </button>
              <label className="action-button">
                <Upload size={36} className="icon" />
                <span className="label">Import</span>
                <input
                  type="file"
                  accept=".txt,.pdf,.doc,.docx,.mp3,.wav"
                  style={{ display: 'none' }}
                  onChange={(e) => console.log("File uploaded:", e.target.files?.[0])}
                />
              </label>
            </div>
          )}

          {recState === 'setup' && (
            <div className="setup-panel">
              <div className="setup-header">
                <span className="setup-title">New Recording</span>
                <button onClick={cancelSetup} className="icon-button"><X size={16} /></button>
              </div>
              <div className="form-group">
                <label className="input-label">Patient Name</label>
                <input type="text" value={patientName} onChange={e => setPatientName(e.target.value)}
                  placeholder="e.g. John Doe" autoFocus
                  className="input-field" />
              </div>
              <div className="form-group">
                <label className="input-label">Patient ID</label>
                <input type="text" value={patientId} onChange={e => setPatientId(e.target.value)}
                  placeholder="e.g. P-00123"
                  onKeyDown={e => e.key === 'Enter' && startRecording()}
                  className="input-field" />
              </div>
              {error && <p className="error-text">{error}</p>}
              <button onClick={startRecording} disabled={!patientName.trim() || !patientId.trim()}
                className="btn btn-danger" style={{ marginTop: '0.5rem' }}>
                <Mic size={15} /> Start Recording
              </button>
            </div>
          )}

          {recState === 'recording' && (
            <div className="recording-active-panel">
              <div className="timer-display">
                <div className="recording-dot" />
                <span className="timer-text">{fmtTime(elapsed)}</span>
                <span className="recording-status">Recording…</span>
              </div>
              <p className="patient-info">{patientName} · {patientId}</p>
              <button onClick={stopRecording} className="btn btn-secondary">
                <Square size={14} style={{ fill: 'currentColor' }} /> Stop Recording
              </button>
            </div>
          )}

          {recState === 'processing' && (
            <div className="processing-panel">
              {steps.map((step, i) => (
                <div key={i} className="processing-step">
                  <div className="step-icon-container">
                    {step.status === 'done'    && <Check size={16} className="step-done" />}
                    {step.status === 'active'  && <Loader2 size={16} className="step-active" />}
                    {step.status === 'pending' && <div className="step-pending-dot" />}
                  </div>
                  <span className={`step-label ${step.status}`}>
                    {step.label}
                  </span>
                </div>
              ))}
            </div>
          )}

        </div>

        {/* Preview panel */}
        <div className="preview-panel">
          <div className="preview-header">
            <span className="recording-dot" style={{ animation: recState === 'recording' ? 'pulse-glow 2s infinite' : 'none', background: recState === 'recording' ? 'var(--danger)' : 'var(--bg-surface-elevated)', boxShadow: 'none' }} />
            <span className="preview-title">
              {recState === 'recording' ? 'Recording in progress' : 'Transcription Preview'}
            </span>
          </div>

          {recState === 'recording' ? (
            <div className="waveform-container">
              <div className="waveform">
                {[3,5,8,5,9,4,7,5,3,6,8,4].map((h, i) => (
                  <div key={i} className="waveform-bar"
                    style={{ height: `${h * 10}%`, animationDelay: `${i * 80}ms` }} />
                ))}
              </div>
              <p className="patient-info">Transcript will appear after processing</p>
            </div>
          ) : (
            <div className="preview-transcript">
              {PREVIEW_LINES.map(({ speaker, text }, i) => (
                <div key={i} className="transcript-line">
                  <span className={`transcript-speaker ${speaker === 'Doctor' ? 'speaker-doctor' : 'speaker-patient'}`}>
                    {speaker}
                  </span>
                  <p className="transcript-text">{text}</p>
                </div>
              ))}
              <div className="transcript-line">
                <span className="transcript-speaker speaker-doctor">Doctor</span>
                <p className="transcript-text italic">Listening<span>...</span></p>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
