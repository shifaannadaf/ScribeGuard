import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText, Clock, CheckCircle2, Mic, Square, X, Loader2, Check,
  Activity, ShieldAlert, AlertCircle, Upload,
} from 'lucide-react'
import {
  createEncounter, getStats, importTranscript, intakeAudio, listRegisteredAgents,
  type DashboardStats, type RegisteredAgent,
} from '../api/encounters'
import { useLiveCaption } from '../hooks/useLiveCaption'
import './Dashboard.css'

type RecordState = 'idle' | 'setup' | 'recording' | 'processing' | 'import-setup'
type Step = { label: string; status: 'pending' | 'active' | 'done' | 'failed'; agent?: string }

const PIPELINE_STEPS: { agent: string; label: string }[] = [
  { agent: 'EncounterIntakeAgent',         label: 'Validating audio (Intake Agent)' },
  { agent: 'TranscriptionAgent',           label: 'Transcribing (Transcription Agent)' },
  { agent: 'ClinicalNoteGenerationAgent',  label: 'Drafting SOAP (Note Generation Agent)' },
  { agent: 'MedicationExtractionAgent',    label: 'Extracting medications (Medication Agent)' },
]

function fmtTime(s: number) {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats]             = useState<DashboardStats | null>(null)
  const [agents, setAgents]           = useState<RegisteredAgent[]>([])
  const [recState, setRecState]       = useState<RecordState>('idle')
  const [patientName, setPatientName] = useState('')
  const [patientId, setPatientId]     = useState('')
  const [openmrsUuid, setOpenmrsUuid] = useState('')
  const [elapsed, setElapsed]         = useState(0)
  const [steps, setSteps]             = useState<Step[]>([])
  const [error, setError]             = useState<string | null>(null)
  const [importFile, setImportFile]   = useState<File | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef        = useRef<Blob[]>([])
  const timerRef         = useRef<ReturnType<typeof setInterval> | null>(null)
  const streamRef        = useRef<MediaStream | null>(null)

  // Live captions via the browser Web Speech API. Runs alongside the
  // server-side Whisper pipeline; UX-only, never used for SOAP generation.
  const caption = useLiveCaption()

  const reload = () => getStats().then(setStats).catch(() => {})
  useEffect(() => { reload() }, [])
  useEffect(() => { listRegisteredAgents().then(r => setAgents(r.agents)).catch(() => {}) }, [])

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
      caption.reset()
      caption.start()
    } catch {
      setError('Microphone access denied. Please allow microphone permissions and try again.')
    }
  }

  function setStep(agent: string, status: Step['status']) {
    setSteps(prev => prev.map(s => s.agent === agent ? { ...s, status } : s))
  }

  async function stopRecording() {
    const mr = mediaRecorderRef.current
    if (!mr) return
    if (timerRef.current) clearInterval(timerRef.current)
    streamRef.current?.getTracks().forEach(t => t.stop())
    caption.stop()

    setSteps(PIPELINE_STEPS.map((s, i) => ({ label: s.label, agent: s.agent, status: i === 0 ? 'active' : 'pending' })))
    setRecState('processing')

    mr.onstop = async () => {
      try {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const enc = await createEncounter(patientName.trim(), patientId.trim(), openmrsUuid || undefined)

        const promise = intakeAudio(enc.id, blob, { autoRun: true })

        // Visual progression heuristic until promise resolves
        let i = 0
        const tick = setInterval(() => {
          i = Math.min(i + 1, PIPELINE_STEPS.length - 1)
          PIPELINE_STEPS.forEach((s, idx) => setStep(s.agent, idx < i ? 'done' : idx === i ? 'active' : 'pending'))
        }, 1100)

        const result = await promise
        clearInterval(tick)

        if ((result.errors || []).length > 0) {
          PIPELINE_STEPS.forEach(s => setStep(s.agent, 'failed'))
          setError(result.errors.join(' · '))
          setRecState('idle')
          return
        }
        PIPELINE_STEPS.forEach(s => setStep(s.agent, 'done'))
        reload()
        setTimeout(() => navigate(`/encounters/${enc.id}`), 500)
      } catch (e: any) {
        setError(e.message ?? 'Pipeline failed')
        setRecState('idle')
        setSteps([])
      }
    }
    mr.stop()
  }

  function cancelSetup() {
    setRecState('idle')
    setPatientName(''); setPatientId(''); setOpenmrsUuid('')
    setImportFile(null)
    setError(null)
  }

  async function importTranscriptFlow() {
    if (!patientName.trim() || !patientId.trim() || !importFile) return
    setError(null)

    setSteps([
      { label: 'Importing transcript',                          agent: 'Import',                       status: 'active'  },
      { label: 'Drafting SOAP (Note Generation Agent)',         agent: 'ClinicalNoteGenerationAgent',  status: 'pending' },
      { label: 'Extracting medications (Medication Agent)',     agent: 'MedicationExtractionAgent',    status: 'pending' },
    ])
    setRecState('processing')

    try {
      const enc = await createEncounter(patientName.trim(), patientId.trim(), openmrsUuid || undefined)
      setStep('Import', 'done')
      setStep('ClinicalNoteGenerationAgent', 'active')

      const result = await importTranscript(enc.id, importFile, { autoRun: true })

      if ((result.errors || []).length > 0) {
        setStep('ClinicalNoteGenerationAgent', 'failed')
        setStep('MedicationExtractionAgent', 'failed')
        setError(result.errors.join(' · '))
        setRecState('idle')
        return
      }
      setStep('ClinicalNoteGenerationAgent', 'done')
      setStep('MedicationExtractionAgent', 'done')
      reload()
      setTimeout(() => navigate(`/encounters/${enc.id}`), 500)
    } catch (e: any) {
      setError(e.message ?? 'Transcript import failed')
      setRecState('idle')
      setSteps([])
    }
  }

  const cards = [
    { label: 'Notes Today',       value: stats?.notes_today       ?? '—', icon: FileText,    colorClass: 'stat-blue'   },
    { label: 'Pending Review',    value: stats?.pending_review    ?? '—', icon: Clock,       colorClass: 'stat-yellow' },
    { label: 'Pushed to OpenMRS', value: stats?.pushed_to_openmrs ?? '—', icon: CheckCircle2,colorClass: 'stat-green'  },
    { label: 'Failed',            value: stats?.failed            ?? '—', icon: ShieldAlert, colorClass: 'stat-purple' },
  ]

  return (
    <div className="dashboard-container">

      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 className="page-title">Agentic Workspace</h1>
            <p className="page-subtitle">Record an encounter — autonomous agents will produce a physician-reviewed SOAP note.</p>
          </div>
          <button onClick={() => navigate('/history')} className="btn btn-primary" style={{ background: 'var(--success)' }}>
            <FileText size={16} /> Open Encounter History
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
        {/* Recording controls */}
        <div className="recording-controls">
          {recState === 'idle' && (
            <div className="action-buttons-row">
              <button onClick={() => setRecState('setup')} className="action-button primary">
                <Mic size={36} className="icon" />
                <span className="label">Record Encounter</span>
              </button>
              <button onClick={() => setRecState('import-setup')} className="action-button primary"
                style={{ background: 'rgba(99,102,241,0.10)', borderColor: 'rgba(99,102,241,0.45)' }}>
                <Upload size={36} className="icon" />
                <span className="label">Import Transcript</span>
              </button>
              <div style={{
                padding: '1rem',
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--border-color, #2a2d3a)',
                borderRadius: 12,
                fontSize: 12,
                color: 'var(--text-muted, #9ca3af)',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
                width: 280,
              }}>
                <strong style={{ color: 'var(--text-strong, #e5e7eb)' }}>Active Agents</strong>
                {agents.length === 0 ? (
                  <span>Loading registry…</span>
                ) : agents.map(a => (
                  <span key={a.name} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Activity size={11} /> {a.name} <code style={{ opacity: 0.65 }}>v{a.version}</code>
                  </span>
                ))}
              </div>
            </div>
          )}

          {recState === 'import-setup' && (
            <div className="setup-panel">
              <div className="setup-header">
                <span className="setup-title">Import Transcript</span>
                <button onClick={cancelSetup} className="icon-button"><X size={16} /></button>
              </div>
              <div className="form-group">
                <label className="input-label">Patient Name</label>
                <input type="text" value={patientName} onChange={e => setPatientName(e.target.value)}
                  placeholder="e.g. John Doe" autoFocus className="input-field" />
              </div>
              <div className="form-group">
                <label className="input-label">Patient ID</label>
                <input type="text" value={patientId} onChange={e => setPatientId(e.target.value)}
                  placeholder="e.g. P-00123" className="input-field" />
              </div>
              <div className="form-group">
                <label className="input-label">OpenMRS Patient UUID <span style={{ opacity: 0.6 }}>(optional)</span></label>
                <input type="text" value={openmrsUuid} onChange={e => setOpenmrsUuid(e.target.value)}
                  placeholder="auto-resolved if omitted" className="input-field" />
              </div>
              <div className="form-group">
                <label className="input-label">
                  Transcript File <span style={{ opacity: 0.6 }}>(any format — txt, md, pdf, docx, srt, vtt, json, html, audio…)</span>
                </label>
                <input type="file"
                  onChange={e => setImportFile(e.target.files?.[0] ?? null)}
                  className="input-field"
                  style={{ padding: 8 }}
                />
                {importFile && (
                  <p style={{ fontSize: 11, color: '#9ca3af', marginTop: 6 }}>
                    Selected: <strong>{importFile.name}</strong> · {(importFile.size / 1024).toFixed(1)} KB
                    {importFile.type ? ` · ${importFile.type}` : ''}
                  </p>
                )}
              </div>
              {error && <p className="error-text">{error}</p>}
              <button onClick={importTranscriptFlow}
                disabled={!patientName.trim() || !patientId.trim() || !importFile}
                className="btn btn-primary" style={{ marginTop: '0.5rem' }}>
                <Upload size={15} /> Import & Run Pipeline
              </button>
            </div>
          )}

          {recState === 'setup' && (
            <div className="setup-panel">
              <div className="setup-header">
                <span className="setup-title">New Encounter</span>
                <button onClick={cancelSetup} className="icon-button"><X size={16} /></button>
              </div>
              <div className="form-group">
                <label className="input-label">Patient Name</label>
                <input type="text" value={patientName} onChange={e => setPatientName(e.target.value)}
                  placeholder="e.g. John Doe" autoFocus className="input-field" />
              </div>
              <div className="form-group">
                <label className="input-label">Patient ID</label>
                <input type="text" value={patientId} onChange={e => setPatientId(e.target.value)}
                  placeholder="e.g. P-00123" className="input-field" />
              </div>
              <div className="form-group">
                <label className="input-label">OpenMRS Patient UUID <span style={{ opacity: 0.6 }}>(optional)</span></label>
                <input type="text" value={openmrsUuid} onChange={e => setOpenmrsUuid(e.target.value)}
                  placeholder="auto-resolved if omitted" className="input-field" />
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

              {/* Live captions (browser Web Speech API). Quality is rough — the
                  canonical transcript still comes from the backend pipeline. */}
              <div style={{
                marginTop: 12, padding: '12px 14px',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--border-color, #2a2d3a)',
                borderRadius: 10,
                minHeight: 96, maxHeight: 180, overflowY: 'auto',
                fontSize: 13, lineHeight: 1.55,
                color: 'var(--text-strong, #e5e7eb)',
                width: '100%', maxWidth: 680,
              }}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between',
                  fontSize: 11, color: '#9ca3af', marginBottom: 6,
                  textTransform: 'uppercase', letterSpacing: 0.5,
                }}>
                  <span>Live Caption {!caption.isSupported && '(unsupported in this browser)'}</span>
                  {caption.isSupported && (
                    <span style={{ color: '#86efac' }}>● live</span>
                  )}
                </div>
                {caption.error && (
                  <p style={{ color: '#fca5a5', fontSize: 12, margin: '0 0 6px' }}>
                    Caption error: {caption.error}
                  </p>
                )}
                {!caption.transcript && !caption.interim && caption.isSupported && (
                  <p style={{ color: '#6b7280', fontStyle: 'italic', margin: 0 }}>
                    Listening… start speaking and words will appear here.
                  </p>
                )}
                {(caption.transcript || caption.interim) && (
                  <p style={{ margin: 0 }}>
                    <span>{caption.transcript}</span>
                    {caption.interim && (
                      <span style={{ color: '#9ca3af', fontStyle: 'italic' }}>
                        {' '}{caption.interim}
                      </span>
                    )}
                  </p>
                )}
              </div>

              <button onClick={stopRecording} className="btn btn-secondary" style={{ marginTop: 12 }}>
                <Square size={14} style={{ fill: 'currentColor' }} /> Stop & Run Pipeline
              </button>
            </div>
          )}

          {recState === 'processing' && (
            <div className="processing-panel">
              {steps.map((step, i) => (
                <div key={i} className="processing-step">
                  <div className="step-icon-container">
                    {step.status === 'done'   && <Check size={16} className="step-done" />}
                    {step.status === 'active' && <Loader2 size={16} className="step-active" />}
                    {step.status === 'failed' && <AlertCircle size={16} color="#ef4444" />}
                    {step.status === 'pending' && <div className="step-pending-dot" />}
                  </div>
                  <span className={`step-label ${step.status}`}>{step.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Agent overview */}
        <div className="preview-panel">
          <div className="preview-header">
            <span className="recording-dot" style={{ background: 'var(--bg-surface-elevated)', boxShadow: 'none' }} />
            <span className="preview-title">How ScribeGuard's agents collaborate</span>
          </div>
          <div style={{
            padding: 16, display: 'flex', flexDirection: 'column', gap: 10,
            color: 'var(--text-strong, #e5e7eb)', fontSize: 13, lineHeight: 1.55,
          }}>
            <p>
              When you click <strong>Stop</strong>, ScribeGuard runs an end-to-end agent pipeline on the server.
              Each step is a focused, autonomous agent persisted as an audited <code>agent_run</code>:
            </p>
            <ol style={{ margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 4 }}>
              <li><strong>Encounter Intake Agent</strong> — validates &amp; stores audio</li>
              <li><strong>Transcription Agent</strong> — Whisper + cleanup + quality flags</li>
              <li><strong>Clinical Note Generation Agent</strong> — GPT-4 SOAP under engineered prompt</li>
              <li><strong>Medication Extraction Agent</strong> — structured drugs from Plan</li>
              <li><strong>Physician Review Agent</strong> — your edits + explicit approval</li>
              <li><strong>OpenMRS Integration Agent</strong> — FHIR write-back &amp; verification</li>
              <li><strong>Audit &amp; Traceability Agent</strong> — durable audit trail</li>
            </ol>
            <p style={{ color: '#9ca3af', fontSize: 12 }}>
              No SOAP note is committed without your explicit approval.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
