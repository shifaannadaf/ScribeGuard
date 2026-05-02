import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search, Filter, Clock, FileText, AlertTriangle, Send, ShieldCheck,
  Trash2, RotateCcw,
} from 'lucide-react'
import {
  listEncounters, deleteEncounter, resetEncounters,
  type EncounterListItem, type EncounterStatus,
} from '../api/encounters'
import { searchPatients, type OpenMRSPatient } from '../api/openmrs'

const STATUS_FILTERS: Array<{ value: '' | EncounterStatus; label: string }> = [
  { value: '',         label: 'All' },
  { value: 'pending',  label: 'Pending Review' },
  { value: 'approved', label: 'Approved' },
  { value: 'pushed',   label: 'Submitted' },
  { value: 'failed',   label: 'Failed' },
]

export default function History() {
  const navigate = useNavigate()
  const [items, setItems] = useState<EncounterListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<'' | EncounterStatus>('')
  const [busyId, setBusyId] = useState<string | null>(null)
  const [resetting, setResetting] = useState(false)

  const reload = () =>
    listEncounters({ status: status || undefined, search: search || undefined })
      .then(r => setItems(r.data))

  useEffect(() => {
    setLoading(true)
    reload().finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, search])

  async function handleDelete(e: React.MouseEvent, id: string, label: string) {
    e.stopPropagation()
    if (!confirm(`Delete encounter "${label}"? This cannot be undone.`)) return
    setBusyId(id)
    try {
      await deleteEncounter(id)
      setItems(prev => prev.filter(i => i.id !== id))
    } catch (err: any) {
      alert(`Delete failed: ${err.message ?? err}`)
    } finally {
      setBusyId(null)
    }
  }

  async function handleReset(scope: 'failed' | 'pushed' | 'approved' | 'pending' | 'all') {
    const verb = scope === 'all' ? 'delete ALL encounters' : `delete every "${scope}" encounter`
    if (!confirm(`Are you sure you want to ${verb}? This cannot be undone.`)) return
    setResetting(true)
    try {
      const res = await resetEncounters(scope === 'all' ? undefined : scope)
      await reload()
      alert(`Removed ${res.deleted} encounter${res.deleted === 1 ? '' : 's'}.`)
    } catch (err: any) {
      alert(`Reset failed: ${err.message ?? err}`)
    } finally {
      setResetting(false)
    }
  }

  return (
    <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <h1 className="page-title">Encounters</h1>
          <p className="page-subtitle">All encounters with their pipeline state, SOAP review status, and OpenMRS submission.</p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <ResetButton label="Clear failed"   onClick={() => handleReset('failed')}   disabled={resetting} tone="danger" />
          <ResetButton label="Clear submitted" onClick={() => handleReset('pushed')}   disabled={resetting} tone="muted" />
          <ResetButton label="Clear all"      onClick={() => handleReset('all')}      disabled={resetting} tone="danger-strong" />
        </div>
      </div>

      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{
          flex: 1, minWidth: 240,
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '0.5rem 0.75rem',
          background: 'var(--bg-surface, #1a1c25)',
          border: '1px solid var(--border-color, #2a2d3a)',
          borderRadius: 8,
        }}>
          <Search size={16} />
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by patient name or ID…"
            style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: 'var(--text-strong, #e5e7eb)' }}
          />
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <Filter size={14} />
          {STATUS_FILTERS.map(f => (
            <button key={f.value} onClick={() => setStatus(f.value)}
              style={{
                padding: '4px 10px',
                fontSize: 12,
                borderRadius: 999,
                background: status === f.value ? '#6366f1' : 'transparent',
                color: status === f.value ? 'white' : '#9ca3af',
                border: `1px solid ${status === f.value ? '#6366f1' : 'var(--border-color, #2a2d3a)'}`,
                cursor: 'pointer',
              }}
            >{f.label}</button>
          ))}
        </div>
      </div>

      {loading && <p style={{ color: '#9ca3af' }}>Loading…</p>}
      {!loading && items.length === 0 && (
        <div style={{
          padding: 32, textAlign: 'center',
          background: 'rgba(255,255,255,0.02)',
          border: '1px dashed var(--border-color, #2a2d3a)',
          borderRadius: 12,
          color: '#9ca3af',
        }}>
          No encounters yet. Record one from the dashboard.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {items.map(it => (
          <div key={it.id}
            onClick={() => navigate(`/encounters/${it.id}`)}
            style={{
              display: 'grid',
              gridTemplateColumns: '1.5fr 1fr 1fr 1.2fr auto auto',
              gap: 10,
              alignItems: 'center',
              padding: '0.75rem 1rem',
              textAlign: 'left',
              background: 'var(--bg-surface, #1a1c25)',
              border: '1px solid var(--border-color, #2a2d3a)',
              borderRadius: 10,
              cursor: 'pointer',
              color: 'inherit',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <strong style={{ color: 'var(--text-strong, #e5e7eb)' }}>{it.patient_name}</strong>
              <span style={{ fontSize: 12, color: '#9ca3af' }}>{it.patient_id}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#9ca3af' }}>
              <Clock size={12} /> {it.date} · {it.time}{it.duration ? ` · ${it.duration}` : ''}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
              <FileText size={12} color="#9ca3af" />
              <span style={{ color: '#9ca3af' }}>
                {it.has_soap_note ? `${it.medication_count} med${it.medication_count === 1 ? '' : 's'}` : 'no SOAP yet'}
              </span>
            </div>
            <span style={{
              padding: '4px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600,
              background: statusTone(it.status).bg, color: statusTone(it.status).fg,
              textAlign: 'center',
            }}>
              {labelFor(it.status)}
            </span>
            <span style={{ fontSize: 11, color: '#9ca3af', textAlign: 'right' }}>
              stage: <code>{it.processing_stage}</code>
            </span>
            <button
              onClick={(e) => handleDelete(e, it.id, `${it.patient_name} (${it.patient_id})`)}
              disabled={busyId === it.id}
              title="Delete this encounter"
              style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                width: 30, height: 30,
                background: 'transparent',
                border: '1px solid var(--border-color, #2a2d3a)',
                borderRadius: 8,
                color: busyId === it.id ? '#6b7280' : '#fca5a5',
                cursor: busyId === it.id ? 'wait' : 'pointer',
              }}
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

function ResetButton({
  label, onClick, disabled, tone,
}: {
  label: string
  onClick: () => void
  disabled?: boolean
  tone: 'danger' | 'danger-strong' | 'muted'
}) {
  const palette = tone === 'danger-strong'
    ? { bg: 'rgba(239,68,68,0.18)', fg: '#fca5a5', border: 'rgba(239,68,68,0.5)' }
    : tone === 'danger'
    ? { bg: 'rgba(239,68,68,0.10)', fg: '#fca5a5', border: 'rgba(239,68,68,0.35)' }
    : { bg: 'transparent',          fg: '#9ca3af', border: 'var(--border-color, #2a2d3a)' }
  return (
    <button onClick={onClick} disabled={disabled}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '6px 12px', fontSize: 12, fontWeight: 600,
        background: palette.bg, color: palette.fg,
        border: `1px solid ${palette.border}`, borderRadius: 8,
        cursor: disabled ? 'wait' : 'pointer', opacity: disabled ? 0.6 : 1,
      }}
    >
      <RotateCcw size={13} /> {label}
    </button>
  )
}

function statusTone(s: EncounterStatus) {
  switch (s) {
    case 'approved': return { bg: 'rgba(99,102,241,0.15)',  fg: '#a5b4fc' }
    case 'pushed':   return { bg: 'rgba(34,197,94,0.15)',   fg: '#86efac' }
    case 'failed':   return { bg: 'rgba(239,68,68,0.15)',   fg: '#fca5a5' }
    default:         return { bg: 'rgba(245,158,11,0.15)',  fg: '#fcd34d' }
  }
}
function labelFor(s: EncounterStatus) {
  switch (s) {
    case 'approved': return <><ShieldCheck size={11} style={{ verticalAlign: -2 }} /> Approved</>
    case 'pushed':   return <><Send size={11} style={{ verticalAlign: -2 }} /> Submitted</>
    case 'failed':   return <><AlertTriangle size={11} style={{ verticalAlign: -2 }} /> Failed</>
    default:         return 'Pending Review'
  }
}
