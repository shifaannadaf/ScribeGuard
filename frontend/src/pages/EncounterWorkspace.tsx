import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, CheckCircle2, Server, RefreshCw, Loader2, AlertCircle,
  ShieldCheck, Send, Undo2, Activity, ScrollText, Pill, ShieldOff,
  Stethoscope, Heart, CalendarClock, ClipboardList,
} from 'lucide-react'
import {
  approveSoap, editSoap, getEncounter, getPipelineStatus, runFullPipeline,
  revertApproval, submitToOpenMRS, getAuditTrail,
  type EncounterDetail, type PipelineStatus, type Medication, type AuditEvent,
} from '../api/encounters'
import AgentTimeline, { AgentRunRow } from '../components/AgentTimeline'
import SoapEditor from '../components/SoapEditor'
import MedicationPanel from '../components/MedicationPanel'
import {
  AllergyPanel, ConditionPanel, VitalsPanel, FollowUpPanel, ExtractionStatus,
} from '../components/EntityPanels'
import PatientContextPanel from '../components/PatientContextPanel'

type Tab = 'review' | 'medications' | 'allergies' | 'conditions' | 'vitals' | 'follow_ups' | 'transcript' | 'agents' | 'audit'

const TABS: Array<{ id: Tab; label: string; icon: any }> = [
  { id: 'review',      label: 'SOAP Review',  icon: ShieldCheck },
  { id: 'medications', label: 'Medications',  icon: Pill },
  { id: 'allergies',   label: 'Allergies',    icon: ShieldOff },
  { id: 'conditions',  label: 'Conditions',   icon: Stethoscope },
  { id: 'vitals',      label: 'Vital Signs',  icon: Heart },
  { id: 'follow_ups',  label: 'Follow-ups',   icon: CalendarClock },
  { id: 'transcript',  label: 'Transcript',   icon: ScrollText },
  { id: 'agents',      label: 'Agents',       icon: Activity },
  { id: 'audit',       label: 'Audit',        icon: Server },
]

export default function EncounterWorkspace() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [encounter, setEncounter] = useState<EncounterDetail | null>(null)
  const [pipeline, setPipeline]   = useState<PipelineStatus | null>(null)
  const [tab, setTab]             = useState<Tab>('review')
  const [loading, setLoading]     = useState(true)
  const [busy, setBusy]           = useState<string | null>(null)
  const [error, setError]         = useState<string | null>(null)
  const [toast, setToast]         = useState<string | null>(null)

  // Pending edits
  const [draftSections, setDraftSections] = useState<Record<string, string> | null>(null)
  const [draftMeds, setDraftMeds] = useState<Medication[] | null>(null)

  const refresh = useCallback(async () => {
    if (!id) return
    try {
      const [enc, pipe] = await Promise.all([getEncounter(id), getPipelineStatus(id)])
      setEncounter(enc); setPipeline(pipe)
      setDraftSections(null); setDraftMeds(null)
      setError(null)
    } catch (e: any) {
      setError(e.message ?? 'Failed to load encounter')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { refresh() }, [refresh])

  // Auto-poll while pipeline is mid-flight
  useEffect(() => {
    if (!encounter) return
    const stage = encounter.processing_stage
    const inFlight = ['transcribing', 'generating_soap', 'extracting_meds', 'submitting'].includes(stage)
    if (!inFlight) return
    const t = setInterval(refresh, 1500)
    return () => clearInterval(t)
  }, [encounter, refresh])

  if (loading) {
    return (
      <div style={{ padding: 32, display: 'flex', alignItems: 'center', gap: 8, color: '#9ca3af' }}>
        <Loader2 size={18} className="step-active" /> Loading encounter…
      </div>
    )
  }
  if (!encounter) {
    return (
      <div style={{ padding: 32 }}>
        <div className="error-text">{error ?? 'Encounter not found'}</div>
        <button className="btn btn-secondary" onClick={() => navigate('/history')}>Back to history</button>
      </div>
    )
  }

  const note = encounter.soap_note
  const isApproved = note?.status === 'approved'
  const submitted = encounter.status === 'pushed'

  async function rerunPipeline() {
    if (!id) return
    setBusy('pipeline'); setError(null)
    try {
      await runFullPipeline(id); await refresh()
      setToast('Pipeline complete')
    } catch (e: any) { setError(e.message ?? 'Pipeline failed') }
    finally { setBusy(null); setTimeout(() => setToast(null), 2200) }
  }

  async function saveEdits() {
    if (!id) return
    setBusy('save'); setError(null)
    try {
      await editSoap(id, {
        sections: draftSections ?? undefined,
        medications: draftMeds ?? undefined,
        actor: 'physician',
      })
      await refresh()
      setToast('Draft saved')
    } catch (e: any) { setError(e.message ?? 'Save failed') }
    finally { setBusy(null); setTimeout(() => setToast(null), 2200) }
  }

  async function approve() {
    if (!id) return
    setBusy('approve'); setError(null)
    try {
      if (draftSections || draftMeds) {
        await editSoap(id, { sections: draftSections ?? undefined, medications: draftMeds ?? undefined, actor: 'physician' })
      }
      await approveSoap(id, { actor: 'physician' })
      await refresh()
      setToast('Note approved')
    } catch (e: any) { setError(e.message ?? 'Approval failed') }
    finally { setBusy(null); setTimeout(() => setToast(null), 2200) }
  }

  async function revert() {
    if (!id) return
    setBusy('revert'); setError(null)
    try {
      await revertApproval(id); await refresh()
      setToast('Reverted to editable')
    } catch (e: any) { setError(e.message ?? 'Revert failed') }
    finally { setBusy(null); setTimeout(() => setToast(null), 2200) }
  }

  async function submit() {
    if (!id) return
    setBusy('submit'); setError(null)
    try {
      const r = await submitToOpenMRS(id, { actor: 'physician' })
      await refresh()
      if (r.status === 'failed') setError(r.error ?? 'OpenMRS submission failed')
      else setToast(`Submitted to OpenMRS · encounter ${r.openmrs_encounter_uuid}`)
    } catch (e: any) { setError(e.message ?? 'Submission failed') }
    finally { setBusy(null); setTimeout(() => setToast(null), 4000) }
  }

  return (
    <div style={{ padding: '1.5rem', display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 320px', gap: 16 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, minWidth: 0 }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button onClick={() => navigate('/history')} className="btn btn-ghost" style={{ padding: 6 }}>
            <ArrowLeft size={18} />
          </button>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <h1 className="page-title" style={{ marginBottom: 2 }}>{encounter.patient_name}</h1>
            <span style={{ color: '#9ca3af', fontSize: 13 }}>
              {encounter.patient_id} · {new Date(encounter.created_at).toLocaleString()}
              {encounter.duration ? ` · ${encounter.duration}` : ''}
              {encounter.openmrs_patient_uuid ? ` · OpenMRS ${encounter.openmrs_patient_uuid.slice(0, 8)}…` : ''}
            </span>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            <button className="btn btn-ghost" onClick={refresh} disabled={!!busy}>
              <RefreshCw size={14} /> Refresh
            </button>
            {!isApproved && (
              <button className="btn btn-primary" onClick={rerunPipeline} disabled={!!busy}>
                {busy === 'pipeline' ? <Loader2 size={14} className="step-active" /> : <Activity size={14} />}
                Re-run pipeline
              </button>
            )}
          </div>
        </div>

        <AgentTimeline currentStage={encounter.processing_stage} runs={pipeline?.agent_runs ?? []} />

        <ExtractionStatus
          meds={encounter.medications.length}
          allergies={encounter.allergies.length}
          conditions={encounter.conditions.length}
          vitals={encounter.vital_signs.length}
          followups={encounter.follow_ups.length}
        />

        {encounter.last_error && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0.75rem 1rem', background: 'rgba(239,68,68,0.10)', border: '1px solid #ef444444', borderRadius: 10, color: '#fca5a5' }}>
            <AlertCircle size={16} />
            <span><strong>Last error:</strong> {encounter.last_error}</span>
          </div>
        )}
        {error && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0.75rem 1rem', background: 'rgba(239,68,68,0.10)', border: '1px solid #ef444444', borderRadius: 10, color: '#fca5a5' }}>
            <AlertCircle size={16} /> {error}
          </div>
        )}
        {toast && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0.75rem 1rem', background: 'rgba(34,197,94,0.10)', border: '1px solid #22c55e44', borderRadius: 10, color: '#86efac' }}>
            <CheckCircle2 size={16} /> {toast}
          </div>
        )}

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 6, borderBottom: '1px solid var(--border-color, #2a2d3a)', flexWrap: 'wrap' }}>
          {TABS.map(({ id: tabId, label, icon: Icon }) => (
            <button key={tabId}
              onClick={() => setTab(tabId)}
              style={{
                padding: '0.5rem 0.9rem', display: 'flex', alignItems: 'center', gap: 6,
                background: 'transparent', border: 'none', cursor: 'pointer',
                borderBottom: `2px solid ${tab === tabId ? '#6366f1' : 'transparent'}`,
                color: tab === tabId ? '#a5b4fc' : '#9ca3af',
                fontSize: 13, fontWeight: 600,
              }}>
              <Icon size={14} /> {label}
            </button>
          ))}
        </div>

        {tab === 'review' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {note ? (
              <SoapEditor note={note} readOnly={isApproved || submitted} onChange={s => setDraftSections(s)} />
            ) : (
              <EmptyState icon={<ScrollText size={28} />} title="No SOAP note yet" hint="Run the pipeline (or upload audio from the dashboard) to generate a draft." />
            )}

            {/* Action bar */}
            <div style={{
              display: 'flex', gap: 10, alignItems: 'center',
              padding: '0.75rem 1rem',
              background: 'var(--bg-surface, #1a1c25)',
              border: '1px solid var(--border-color, #2a2d3a)',
              borderRadius: 10,
            }}>
              <span style={{ fontSize: 12, color: '#9ca3af' }}>
                Status: <strong style={{ color: '#e5e7eb' }}>{encounter.status}</strong> · Stage: <strong style={{ color: '#e5e7eb' }}>{encounter.processing_stage}</strong>
              </span>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                {!isApproved && !submitted && (
                  <>
                    <button className="btn btn-ghost" disabled={!!busy || (!draftSections && !draftMeds)} onClick={saveEdits}>
                      {busy === 'save' ? <Loader2 size={14} className="step-active" /> : null}
                      Save edits
                    </button>
                    <button className="btn btn-primary" disabled={!!busy || !note} onClick={approve}>
                      {busy === 'approve' ? <Loader2 size={14} className="step-active" /> : <ShieldCheck size={14} />}
                      Approve & Lock
                    </button>
                  </>
                )}
                {isApproved && !submitted && (
                  <>
                    <button className="btn btn-ghost" disabled={!!busy} onClick={revert}>
                      {busy === 'revert' ? <Loader2 size={14} className="step-active" /> : <Undo2 size={14} />}
                      Revert approval
                    </button>
                    <button className="btn btn-primary" style={{ background: '#16a34a' }} disabled={!!busy} onClick={submit}>
                      {busy === 'submit' ? <Loader2 size={14} className="step-active" /> : <Send size={14} />}
                      Submit to OpenMRS
                    </button>
                  </>
                )}
                {submitted && encounter.submission && (
                  <span style={{ color: '#86efac', fontSize: 12 }}>
                    Submitted · OpenMRS encounter <code>{encounter.submission.openmrs_encounter_uuid?.slice(0, 14)}…</code>
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {tab === 'medications' && (
          <MedicationPanel
            medications={draftMeds ?? encounter.medications}
            readOnly={isApproved || submitted}
            onChange={(next) => setDraftMeds(next)}
          />
        )}

        {tab === 'allergies'  && <AllergyPanel  items={encounter.allergies} />}
        {tab === 'conditions' && <ConditionPanel items={encounter.conditions} />}
        {tab === 'vitals'     && <VitalsPanel    items={encounter.vital_signs} />}
        {tab === 'follow_ups' && <FollowUpPanel  items={encounter.follow_ups} />}

        {tab === 'transcript' && (
          <div style={{
            padding: 16,
            background: 'var(--bg-surface, #1a1c25)',
            border: '1px solid var(--border-color, #2a2d3a)',
            borderRadius: 10,
          }}>
            {encounter.transcript ? (
              <>
                <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#9ca3af', marginBottom: 10, flexWrap: 'wrap' }}>
                  <span>Whisper · {encounter.transcript.model}</span>
                  <span>· {encounter.transcript.word_count ?? 0} words</span>
                  {encounter.transcript.duration_seconds != null && (
                    <span>· {encounter.transcript.duration_seconds.toFixed(1)}s audio</span>
                  )}
                  {encounter.transcript.quality_score != null && (
                    <span>· quality {(encounter.transcript.quality_score * 100).toFixed(0)}%</span>
                  )}
                </div>
                {(encounter.transcript.quality_issues || []).length > 0 && (
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
                    {(encounter.transcript.quality_issues || []).map(i => (
                      <span key={i} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999, background: 'rgba(245,158,11,0.15)', color: '#fbbf24' }}>{i}</span>
                    ))}
                  </div>
                )}
                <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 13.5, lineHeight: 1.6, color: 'var(--text-strong, #e5e7eb)' }}>
                  {encounter.transcript.formatted_text || encounter.transcript.raw_text}
                </pre>
              </>
            ) : (
              <EmptyState icon={<ScrollText size={28} />} title="No transcript yet" hint="Upload audio on the dashboard, then re-run the pipeline." />
            )}
          </div>
        )}

        {tab === 'agents' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(pipeline?.agent_runs ?? []).length === 0
              ? <EmptyState icon={<Activity size={28} />} title="No agent runs yet" hint="" />
              : (pipeline?.agent_runs ?? []).map(r => <AgentRunRow key={r.id} run={r} />)}
          </div>
        )}

        {tab === 'audit' && <AuditTab encounterId={encounter.id} />}
      </div>

      {/* Sidebar — patient OpenMRS chart */}
      <PatientContextPanel
        encounterId={encounter.id}
        snapshot={encounter.patient_context}
        onRefreshed={refresh}
      />
    </div>
  )
}

function EmptyState({ icon, title, hint }: { icon: React.ReactNode; title: string; hint: string }) {
  return (
    <div style={{
      padding: 32, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
      background: 'rgba(255,255,255,0.02)', border: '1px dashed var(--border-color, #2a2d3a)', borderRadius: 12,
      color: '#9ca3af',
    }}>
      <span style={{ opacity: 0.7 }}>{icon}</span>
      <strong style={{ color: '#e5e7eb' }}>{title}</strong>
      {hint && <span style={{ fontSize: 13 }}>{hint}</span>}
    </div>
  )
}

function AuditTab({ encounterId }: { encounterId: string }) {
  const [events, setEvents] = useState<AuditEvent[] | null>(null)
  useEffect(() => {
    getAuditTrail(encounterId).then(r => setEvents(r.events)).catch(() => setEvents([]))
  }, [encounterId])
  if (!events) return <div style={{ color: '#9ca3af', fontSize: 13 }}>Loading…</div>
  if (events.length === 0) return <EmptyState icon={<ClipboardList size={28} />} title="No audit events yet" hint="" />
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {events.map(e => (
        <div key={e.id} style={{
          display: 'grid',
          gridTemplateColumns: '160px 200px 1fr',
          gap: 12,
          padding: '0.5rem 0.75rem',
          fontSize: 12,
          background: 'var(--bg-surface, #1a1c25)',
          border: '1px solid var(--border-color, #2a2d3a)',
          borderRadius: 8,
        }}>
          <span style={{ color: '#9ca3af' }}>{new Date(e.created_at).toLocaleString()}</span>
          <span style={{ color: e.severity === 'error' ? '#fca5a5' : '#a5b4fc', fontWeight: 600 }}>
            {e.event_type}{e.agent_name ? ` · ${e.agent_name}` : ''}
          </span>
          <span style={{ color: '#e5e7eb' }}>{e.summary}</span>
        </div>
      ))}
    </div>
  )
}
