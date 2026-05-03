import { Bot, CheckCircle2, Loader2, XCircle, Clock, ChevronRight } from 'lucide-react'
import type { AgentRun, ProcessingStage } from '../api/encounters'

const PIPELINE_STAGES: { stage: ProcessingStage; label: string; agent: string }[] = [
  { stage: 'audio_received',   label: 'Intake',         agent: 'EncounterIntakeAgent' },
  { stage: 'transcribed',      label: 'Transcription',  agent: 'TranscriptionAgent' },
  { stage: 'soap_drafted',     label: 'SOAP Draft',     agent: 'ClinicalNoteGenerationAgent' },
  { stage: 'ready_for_review', label: 'Medications',    agent: 'MedicationExtractionAgent' },
  { stage: 'approved',         label: 'Physician Approval', agent: 'PhysicianReviewAgent' },
  { stage: 'submitted',        label: 'OpenMRS Submission', agent: 'OpenMRSIntegrationAgent' },
]

const STAGE_ORDER: ProcessingStage[] = [
  'created', 'audio_received',
  'transcribing', 'transcribed',
  'generating_soap', 'soap_drafted',
  'extracting_meds', 'ready_for_review',
  'in_review', 'approved',
  'submitting', 'submitted',
  'failed',
]

function stageIndex(s: ProcessingStage): number {
  const i = STAGE_ORDER.indexOf(s)
  return i < 0 ? 0 : i
}

interface Props {
  currentStage: ProcessingStage
  runs: AgentRun[]
}

export default function AgentTimeline({ currentStage, runs }: Props) {
  const cur = stageIndex(currentStage)
  return (
    <div style={{
      display: 'flex',
      gap: '0.5rem',
      flexWrap: 'wrap',
      padding: '0.75rem',
      background: 'var(--bg-surface, #1a1c25)',
      borderRadius: 12,
      border: '1px solid var(--border-color, #2a2d3a)',
    }}>
      {PIPELINE_STAGES.map((s, i) => {
        const stageIdx = stageIndex(s.stage)
        const terminalDone = currentStage === 'submitted'
        const done   = stageIdx < cur || (stageIdx === cur && terminalDone)
        const active = stageIdx === cur && !terminalDone
        const failed = currentStage === 'failed' && i === PIPELINE_STAGES.findIndex(p => p.stage === STAGE_ORDER[Math.max(cur, 0)])
        const lastRun = [...runs].reverse().find(r => r.agent_name === s.agent)
        const ms = lastRun?.duration_ms != null ? `${(lastRun.duration_ms / 1000).toFixed(1)}s` : ''
        return (
          <div key={s.stage} style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '0.5rem 0.75rem',
            borderRadius: 8,
            background: active ? 'rgba(99,102,241,0.15)' : done ? 'rgba(34,197,94,0.10)' : 'transparent',
            border: `1px solid ${active ? '#6366f1' : done ? '#22c55e44' : 'var(--border-color, #2a2d3a)'}`,
            color: active ? '#a5b4fc' : done ? '#86efac' : 'var(--text-muted, #9ca3af)',
            minWidth: 140,
          }}>
            <span style={{ display: 'inline-flex', width: 18, height: 18 }}>
              {failed
                ? <XCircle size={18} color="#ef4444" />
                : active
                  ? <Loader2 size={18} className="step-active" />
                  : done
                    ? <CheckCircle2 size={18} color="#22c55e" />
                    : <Clock size={18} />}
            </span>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: 12, fontWeight: 600 }}>{s.label}</span>
              <span style={{ fontSize: 10, opacity: 0.75 }}>{s.agent}{ms ? ` · ${ms}` : ''}</span>
            </div>
            {i < PIPELINE_STAGES.length - 1 && (
              <ChevronRight size={14} style={{ opacity: 0.4, marginLeft: 'auto' }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

interface AgentRunRowProps { run: AgentRun }

export function AgentRunRow({ run }: AgentRunRowProps) {
  const dur = run.duration_ms ? `${(run.duration_ms / 1000).toFixed(2)}s` : '—'
  const tone =
    run.status === 'succeeded' ? '#22c55e' :
    run.status === 'failed'    ? '#ef4444' :
    run.status === 'running'   ? '#6366f1' : '#9ca3af'
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '24px minmax(0,1fr) auto auto',
      gap: 10,
      alignItems: 'center',
      padding: '0.5rem 0.75rem',
      borderRadius: 8,
      background: 'var(--bg-surface, #1a1c25)',
      border: '1px solid var(--border-color, #2a2d3a)',
      fontSize: 13,
    }}>
      <Bot size={16} color={tone} />
      <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <span style={{ fontWeight: 600, color: 'var(--text-strong, #e5e7eb)' }}>{run.agent_name}</span>
        <span style={{ fontSize: 11, color: 'var(--text-muted, #9ca3af)' }}>
          v{run.agent_version ?? '?'} · attempt {run.attempt}
          {run.error_message ? ` · ${run.error_type}: ${run.error_message}` : ''}
        </span>
      </div>
      <span style={{ fontSize: 11, color: 'var(--text-muted, #9ca3af)' }}>{dur}</span>
      <span style={{
        padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 600,
        background: `${tone}22`, color: tone,
      }}>
        {run.status}
      </span>
    </div>
  )
}
