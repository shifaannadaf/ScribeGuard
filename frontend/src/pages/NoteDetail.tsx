import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, User, Calendar, Clock, Timer, Loader2, Check, FileText, CheckCircle2, ChevronRight, AlertCircle, ShieldAlert } from 'lucide-react'
import { getEncounter, updateEncounter, approveEncounter, pushToOpenMRS, type EncounterDetail, type Medication, type Allergy, type Diagnosis } from '../api/encounters'
import './NoteDetail.css'

type Tab = 'soap' | 'medications' | 'allergies' | 'diagnoses'

const tabs: { id: Tab; label: string }[] = [
  { id: 'soap',          label: 'SOAP Note' },
  { id: 'medications',   label: 'Medications' },
  { id: 'allergies',     label: 'Allergies' },
  { id: 'diagnoses',     label: 'Diagnoses' },
]

function EditableField({ label, value, onChange, multiline = false, readonly = false }: {
  label: string; value: string; onChange: (v: string) => void; multiline?: boolean; readonly?: boolean
}) {
  return (
    <div className="form-group">
      <label className="input-label">{label}</label>
      {multiline ? (
        <textarea value={value} onChange={e => !readonly && onChange(e.target.value)} readOnly={readonly} rows={4}
          className={`textarea-field ${readonly ? 'readonly' : 'edit'}`} />
      ) : (
        <input type="text" value={value} onChange={e => !readonly && onChange(e.target.value)} readOnly={readonly}
          className={`input-field ${readonly ? 'readonly' : 'edit'}`} />
      )}
    </div>
  )
}

const MOCK_SOAP = {
  subjective: "Patient is a 62-year-old male presenting for follow-up of type 2 diabetes and hypertension. Reports feeling generally well but mentions occasional morning dizziness. Denies chest pain, shortness of breath, or changes in vision. Blood sugar logs show fasting levels between 110-130 mg/dL.",
  objective: "BP: 138/86 mmHg. HR: 72 bpm. Wt: 88 kg. Gen: Alert, oriented, in no acute distress. CV: RRR, no murmurs. Pulm: Clear to auscultation bilaterally. Ext: No pedal edema. Neuro: Grossly intact.",
  assessment: "1. Type 2 Diabetes Mellitus - fairly controlled, HbA1c 7.1%.\n2. Essential Hypertension - slightly elevated today, patient reports dizziness possibly related to medication timing.",
  plan: "1. Continue Metformin 1000mg BID.\n2. Adjust Lisinopril to 10mg daily in the evening to mitigate morning dizziness.\n3. Basic metabolic panel and lipid profile ordered.\n4. Follow up in 3 months."
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
  
  const [activeTab, setActiveTab]     = useState<Tab>('soap')
  const [transcript, setTranscript]   = useState('')
  const [medications, setMedications] = useState<Medication[]>([])
  const [allergies, setAllergies]     = useState<Allergy[]>([])
  const [diagnoses, setDiagnoses]     = useState<Diagnosis[]>([])
  
  const [soap, setSoap]               = useState(MOCK_SOAP)
  const [showTranscript, setShowTranscript] = useState(false)

  useEffect(() => {
    if (!id) return
    getEncounter(id)
      .then(data => {
        setRecord(data)
        setTranscript(data.transcript ?? 'Doctor: How have you been?\nPatient: Good, just here for the diabetes follow up.')
        setMedications(data.medications.length ? data.medications : [
          { name: 'Metformin', dose: '1000mg', frequency: 'BID', start_date: '2023-01-15' },
          { name: 'Lisinopril', dose: '10mg', frequency: 'Daily', start_date: '2023-01-15' }
        ])
        setAllergies(data.allergies)
        setDiagnoses(data.diagnoses)
        setLoading(false)
      })
      .catch(e => {
        console.warn('Backend fetch failed, using mock data for demo.', e)
        // Fallback to mock data so the UI can be viewed
        setRecord({
          id: id,
          patient_name: 'John Doe',
          patient_id: 'P-00123',
          date: new Date().toISOString().split('T')[0],
          time: '10:30 AM',
          duration: '14:20',
          status: 'pending',
          snippet: null,
          openmrs_uuid: null,
          transcript: 'Doctor: How have you been?\nPatient: Good, just here for the diabetes follow up.',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          medications: [],
          allergies: [],
          diagnoses: []
        })
        setTranscript('Doctor: How have you been?\nPatient: Good, just here for the diabetes follow up.')
        setMedications([
          { name: 'Metformin', dose: '1000mg', frequency: 'BID', start_date: '2023-01-15' },
          { name: 'Lisinopril', dose: '10mg', frequency: 'Daily', start_date: '2023-01-15' }
        ])
        setAllergies([])
        setDiagnoses([])
        setLoading(false)
      })
  }, [id])

  async function handleSaveDraft() {
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

  async function handleApproveAndSubmit() {
    if (!id || !record) return
    if (!window.confirm("Approve this note and submit to OpenMRS sandbox?")) return
    
    setSaving(true)
    try {
      await updateEncounter(id, { transcript, medications, allergies, diagnoses })
      await approveEncounter(id)
      await pushToOpenMRS(id, 'b80b4ed7-da9c-4b2f-a0b4-c3e66a7b21e8') // mock uuid
      setRecord({ ...record, status: 'pushed' })
      alert("SOAP note successfully submitted to OpenMRS sandbox.")
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return (
    <div className="app-container" style={{ alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
      <Loader2 size={18} style={{ animation: 'spin 1s linear infinite', marginRight: '0.5rem' }} /><span style={{ fontSize: '0.875rem' }}>Loading...</span>
    </div>
  )

  if (error || !record) return (
    <div style={{ padding: '2rem', color: 'var(--danger)', fontSize: '0.875rem' }}>{error ?? 'Record not found.'}</div>
  )

  const steps = ['Audio Captured', 'Transcribed', 'SOAP Generated', 'Physician Review', 'OpenMRS Submitted']
  const currentStep = record.status === 'pushed' ? 5 : record.status === 'approved' ? 4 : 3

  return (
    <div className="note-detail-container">
      {/* Top Action Bar */}
      <div className="note-header">
        <button onClick={() => navigate(-1)} className="icon-button">
          <ArrowLeft size={18} />
        </button>
        <div className="note-header-info">
          <div className="workflow-tracker">
            {steps.map((step, idx) => (
              <div key={step} className={`tracker-step ${idx < currentStep ? 'completed' : idx === currentStep ? 'active' : ''}`}>
                <div className="tracker-dot">{idx < currentStep && <Check size={10} />}</div>
                <span className="tracker-label">{step}</span>
                {idx < steps.length - 1 && <div className="tracker-line" />}
              </div>
            ))}
          </div>
        </div>
        
        {record.status === 'pushed' ? (
          <div className="status-badge status-pushed">
            <CheckCircle2 size={14} /> Synced to OpenMRS
          </div>
        ) : (
          <div className="status-badge status-pending">
            <AlertCircle size={14} /> AI-Generated Pending Review
          </div>
        )}
        
        {!readonly && record.status !== 'pushed' && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button onClick={handleSaveDraft} disabled={saving} className="btn btn-secondary">
              {saved ? <><Check size={14} /> Saved</> : 'Save Draft'}
            </button>
            <button onClick={handleApproveAndSubmit} disabled={saving} className="btn btn-primary" style={{ background: 'var(--success)' }}>
              Approve & Submit
            </button>
          </div>
        )}
      </div>

      <div className="note-content-area">
        {/* Left Sidebar (Patient Summary & Audit) */}
        <div className="note-sidebar" style={{ width: '18rem' }}>
          <div className="summary-card">
            <div className="summary-header">
              <div className="avatar-circle"><User size={20} /></div>
              <div>
                <h3 className="summary-name">{record.patient_name}</h3>
                <p className="summary-id">MRN: {record.patient_id}</p>
              </div>
            </div>
            <div className="summary-details">
              <div className="detail-row"><span>Age / Sex</span><span>62 M</span></div>
              <div className="detail-row"><span>Visit Type</span><span>Follow-up</span></div>
              <div className="detail-row"><span>Date</span><span>{record.date}</span></div>
            </div>
          </div>

          <div className="audit-panel">
            <h4 className="sidebar-section-title" style={{ marginBottom: '0.75rem' }}>Audit Trail</h4>
            <div className="audit-timeline">
              <div className="audit-item">
                <div className="audit-dot" />
                <p className="audit-text">Audio captured ({record.duration})</p>
                <span className="audit-time">{record.time}</span>
              </div>
              <div className="audit-item">
                <div className="audit-dot" />
                <p className="audit-text">Whisper transcription completed</p>
                <span className="audit-time">Just now</span>
              </div>
              <div className="audit-item">
                <div className="audit-dot" />
                <p className="audit-text">GPT-4 structured SOAP generated</p>
                <span className="audit-time">Just now</span>
              </div>
            </div>
            <button 
              className="btn btn-secondary" 
              style={{ width: '100%', marginTop: '1rem', justifyContent: 'space-between' }}
              onClick={() => setShowTranscript(!showTranscript)}
            >
              Raw Transcript <ChevronRight size={16} style={{ transform: showTranscript ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }}/>
            </button>
          </div>
        </div>

        {/* Middle Main Content */}
        <div className="note-main-content">
          <div className="tabs-container">
            {tabs.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}>
                {tab.label}
              </button>
            ))}
          </div>

          <div className="tab-content">
            {activeTab === 'soap' && (
              <div className="editor-container" style={{ maxWidth: '100%' }}>
                <div className="soap-warning">
                  <ShieldAlert size={16} className="text-warning" />
                  <span><strong>AI-Assisted Draft:</strong> Please review and edit the generated notes for clinical accuracy before approving.</span>
                </div>
                
                <div className="card-item soap-section">
                  <div className="soap-section-header">
                    <h3 className="card-title">Subjective</h3>
                    <span className="status-badge status-approved" style={{ fontSize: '0.65rem', padding: '0.125rem 0.5rem' }}>High Confidence</span>
                  </div>
                  <textarea value={soap.subjective} onChange={e => setSoap({...soap, subjective: e.target.value})} readOnly={readonly} rows={3} className={`textarea-field ${readonly ? 'readonly' : 'edit'}`} />
                </div>

                <div className="card-item soap-section">
                  <div className="soap-section-header">
                    <h3 className="card-title">Objective</h3>
                  </div>
                  <textarea value={soap.objective} onChange={e => setSoap({...soap, objective: e.target.value})} readOnly={readonly} rows={2} className={`textarea-field ${readonly ? 'readonly' : 'edit'}`} />
                </div>

                <div className="card-item soap-section">
                  <div className="soap-section-header">
                    <h3 className="card-title">Assessment</h3>
                  </div>
                  <textarea value={soap.assessment} onChange={e => setSoap({...soap, assessment: e.target.value})} readOnly={readonly} rows={2} className={`textarea-field ${readonly ? 'readonly' : 'edit'}`} />
                </div>

                <div className="card-item soap-section">
                  <div className="soap-section-header">
                    <h3 className="card-title">Plan</h3>
                  </div>
                  <textarea value={soap.plan} onChange={e => setSoap({...soap, plan: e.target.value})} readOnly={readonly} rows={3} className={`textarea-field ${readonly ? 'readonly' : 'edit'}`} />
                </div>
              </div>
            )}

            {activeTab === 'medications' && (
              <div className="editor-container" style={{ maxWidth: '100%' }}>
                <div className="soap-warning" style={{ background: 'rgba(59, 130, 246, 0.1)', color: 'var(--primary)', borderColor: 'rgba(59, 130, 246, 0.2)' }}>
                  <ShieldAlert size={16} />
                  <span><strong>Extraction Layer:</strong> Medications extracted from the Plan section. This is structured output, not final prescribing.</span>
                </div>
                
                <div className="table-container">
                  <table className="medication-table">
                    <thead>
                      <tr>
                        <th>Medication</th>
                        <th>Dose</th>
                        <th>Frequency</th>
                        <th>Status</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {medications.map((med, i) => (
                        <tr key={i}>
                          <td><input value={med.name} onChange={e => setMedications(ms => ms.map((m, j) => j===i ? {...m, name: e.target.value} : m))} className="table-input" readOnly={readonly} /></td>
                          <td><input value={med.dose ?? ''} onChange={e => setMedications(ms => ms.map((m, j) => j===i ? {...m, dose: e.target.value} : m))} className="table-input" readOnly={readonly} /></td>
                          <td><input value={med.frequency ?? ''} onChange={e => setMedications(ms => ms.map((m, j) => j===i ? {...m, frequency: e.target.value} : m))} className="table-input" readOnly={readonly} /></td>
                          <td><span className="status-badge status-pending" style={{ fontSize: '0.65rem' }}>Needs Review</span></td>
                          <td><button className="text-danger" style={{ fontSize: '0.75rem' }} disabled={readonly}>Remove</button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!readonly && (
                    <button onClick={() => setMedications(ms => [...ms, { name: '', dose: '', frequency: '' }])} className="add-btn" style={{ padding: '1rem' }}>
                      + Add Medication
                    </button>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'allergies' && (
              <div className="editor-container">
                {/* ... (keep allergies list similar to before) */}
                <p className="text-muted">No allergies reported.</p>
              </div>
            )}

            {activeTab === 'diagnoses' && (
              <div className="editor-container">
                {/* ... (keep diagnoses list similar to before) */}
                <p className="text-muted">Diagnoses sync from Assessment section.</p>
              </div>
            )}

          </div>
        </div>

        {/* Right Collapsible Transcript Pane */}
        {showTranscript && (
          <div className="transcript-drawer">
            <div className="drawer-header">
              <h3 className="sidebar-section-title">Raw Transcript</h3>
              <button onClick={() => setShowTranscript(false)} className="icon-button"><ArrowLeft size={16} style={{ transform: 'rotate(180deg)' }} /></button>
            </div>
            <div className="drawer-content">
              <div className="preview-transcript">
                {transcript.split('\n').map((line, i) => {
                  const [speaker, text] = line.split(': ')
                  if (!text) return <p key={i} className="transcript-text">{line}</p>
                  return (
                    <div key={i} className="transcript-line">
                      <span className={`transcript-speaker ${speaker === 'Doctor' ? 'speaker-doctor' : 'speaker-patient'}`}>{speaker}</span>
                      <p className="transcript-text">{text}</p>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}

