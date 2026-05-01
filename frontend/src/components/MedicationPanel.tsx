import { Pill, Plus, Trash2 } from 'lucide-react'
import type { Medication } from '../api/encounters'

interface Props {
  medications: Medication[]
  readOnly?: boolean
  onChange?: (next: Medication[]) => void
}

const EMPTY_MED: Medication = {
  id: -1,
  name: '',
  dose: '',
  route: '',
  frequency: '',
  duration: '',
  start_date: '',
  indication: '',
  raw_text: '',
  confidence: 'high',
}

export default function MedicationPanel({ medications, readOnly, onChange }: Props) {
  const update = (i: number, patch: Partial<Medication>) => {
    if (!onChange) return
    const copy = medications.slice()
    copy[i] = { ...copy[i], ...patch }
    onChange(copy)
  }
  const remove = (i: number) => onChange?.(medications.filter((_, idx) => idx !== i))
  const add = () => onChange?.([...medications, { ...EMPTY_MED, id: -1 - medications.length }])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Pill size={16} />
        <strong>Medications extracted from Plan</strong>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: '#9ca3af' }}>
          {medications.length} item{medications.length === 1 ? '' : 's'}
        </span>
        {!readOnly && (
          <button
            type="button"
            onClick={add}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              padding: '4px 10px', borderRadius: 999, fontSize: 12,
              background: 'rgba(99,102,241,0.15)', color: '#a5b4fc',
              border: '1px solid #6366f155', cursor: 'pointer',
            }}
          >
            <Plus size={12} /> Add
          </button>
        )}
      </div>

      {medications.length === 0 && (
        <div style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: 8, fontSize: 13, color: '#9ca3af' }}>
          No medications detected in this encounter.
        </div>
      )}

      {medications.map((m, i) => (
        <div key={m.id} style={{
          display: 'grid',
          gridTemplateColumns: '1.4fr 0.8fr 0.7fr 1fr 0.9fr 1fr auto auto',
          gap: 6,
          alignItems: 'center',
          padding: '0.5rem',
          background: 'var(--bg-surface, #1a1c25)',
          border: '1px solid var(--border-color, #2a2d3a)',
          borderRadius: 8,
        }}>
          <input value={m.name}        readOnly={readOnly} placeholder="Name"        onChange={e => update(i, { name: e.target.value })}        style={fieldStyle} />
          <input value={m.dose ?? ''}  readOnly={readOnly} placeholder="Dose"        onChange={e => update(i, { dose: e.target.value })}        style={fieldStyle} />
          <input value={m.route ?? ''} readOnly={readOnly} placeholder="Route"       onChange={e => update(i, { route: e.target.value })}       style={fieldStyle} />
          <input value={m.frequency ?? ''} readOnly={readOnly} placeholder="Frequency" onChange={e => update(i, { frequency: e.target.value })} style={fieldStyle} />
          <input value={m.duration ?? ''} readOnly={readOnly} placeholder="Duration"  onChange={e => update(i, { duration: e.target.value })}    style={fieldStyle} />
          <input value={m.indication ?? ''} readOnly={readOnly} placeholder="Indication" onChange={e => update(i, { indication: e.target.value })} style={fieldStyle} />
          <span style={{
            padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 600,
            background: confidenceTone(m.confidence).bg, color: confidenceTone(m.confidence).fg,
            textTransform: 'capitalize',
          }}>
            {m.confidence ?? 'medium'}
          </span>
          {!readOnly && (
            <button type="button" onClick={() => remove(i)} style={iconBtnStyle} aria-label="Remove">
              <Trash2 size={14} />
            </button>
          )}
        </div>
      ))}
    </div>
  )
}

const fieldStyle: React.CSSProperties = {
  padding: '0.4rem 0.5rem',
  fontSize: 12,
  border: '1px solid var(--border-color, #2a2d3a)',
  background: 'rgba(255,255,255,0.02)',
  color: 'var(--text-strong, #e5e7eb)',
  borderRadius: 6,
  width: '100%',
}

const iconBtnStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  color: '#9ca3af',
  cursor: 'pointer',
  padding: 4,
}

function confidenceTone(c: string | null) {
  switch ((c || '').toLowerCase()) {
    case 'high':   return { bg: 'rgba(34,197,94,0.15)',  fg: '#86efac' }
    case 'low':    return { bg: 'rgba(239,68,68,0.15)',  fg: '#fca5a5' }
    case 'medium':
    default:       return { bg: 'rgba(245,158,11,0.15)', fg: '#fcd34d' }
  }
}
