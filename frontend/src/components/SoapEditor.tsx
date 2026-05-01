import { useEffect, useState } from 'react'
import { ShieldAlert, AlertTriangle, RotateCcw } from 'lucide-react'
import type { SoapSections } from '../api/encounters'

interface Props {
  note: SoapSections
  readOnly?: boolean
  onChange: (next: { subjective: string; objective: string; assessment: string; plan: string }) => void
}

const SECTIONS: Array<{ key: keyof Pick<SoapSections, 'subjective' | 'objective' | 'assessment' | 'plan'>; label: string; rows: number }> = [
  { key: 'subjective', label: 'Subjective', rows: 5 },
  { key: 'objective',  label: 'Objective',  rows: 5 },
  { key: 'assessment', label: 'Assessment', rows: 4 },
  { key: 'plan',       label: 'Plan',       rows: 6 },
]

export default function SoapEditor({ note, readOnly, onChange }: Props) {
  const [draft, setDraft] = useState({
    subjective: note.subjective,
    objective:  note.objective,
    assessment: note.assessment,
    plan:       note.plan,
  })
  const [originals] = useState({
    subjective: note.subjective,
    objective:  note.objective,
    assessment: note.assessment,
    plan:       note.plan,
  })

  useEffect(() => {
    setDraft({
      subjective: note.subjective,
      objective:  note.objective,
      assessment: note.assessment,
      plan:       note.plan,
    })
  }, [note.id])

  const lowConf = new Set((note.low_confidence_sections || []).map(s => s.toLowerCase()))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '0.75rem 1rem',
        background: note.status === 'approved' ? 'rgba(34,197,94,0.10)' : 'rgba(245,158,11,0.10)',
        border: `1px solid ${note.status === 'approved' ? '#22c55e44' : '#f59e0b44'}`,
        borderRadius: 10,
        color: note.status === 'approved' ? '#86efac' : '#fbbf24',
        fontSize: 13,
      }}>
        <ShieldAlert size={16} />
        {note.status === 'approved'
          ? <span><strong>Approved by physician</strong> — locked. Revert to edit.</span>
          : <span><strong>AI-Generated · Pending Review</strong> — every section is editable. Nothing leaves ScribeGuard until you approve.</span>}
        <span style={{ marginLeft: 'auto', fontSize: 11, opacity: 0.8 }}>
          v{note.version} · {note.model}
        </span>
      </div>

      {SECTIONS.map(({ key, label, rows }) => {
        const value = draft[key]
        const isEdited = value !== originals[key]
        return (
          <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <label style={{ fontWeight: 600, fontSize: 13 }}>{label}</label>
              {lowConf.has(key) && (
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  fontSize: 11, color: '#f59e0b',
                }}>
                  <AlertTriangle size={12} /> low confidence — please verify
                </span>
              )}
              {isEdited && !readOnly && (
                <button
                  type="button"
                  onClick={() => {
                    const next = { ...draft, [key]: originals[key] }
                    setDraft(next); onChange(next)
                  }}
                  style={{
                    marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 4,
                    background: 'transparent', border: 'none', color: '#9ca3af',
                    cursor: 'pointer', fontSize: 11,
                  }}
                  title="Revert this section to the AI draft"
                >
                  <RotateCcw size={12} /> Revert
                </button>
              )}
            </div>
            <textarea
              readOnly={readOnly}
              rows={rows}
              value={value}
              onChange={e => {
                const next = { ...draft, [key]: e.target.value }
                setDraft(next); onChange(next)
              }}
              style={{
                width: '100%',
                resize: 'vertical',
                padding: '0.65rem 0.75rem',
                fontFamily: 'inherit',
                fontSize: 13.5,
                lineHeight: 1.5,
                color: 'var(--text-strong, #e5e7eb)',
                background: readOnly ? 'rgba(255,255,255,0.03)' : 'rgba(255,255,255,0.02)',
                border: `1px solid ${isEdited ? '#6366f1' : 'var(--border-color, #2a2d3a)'}`,
                borderRadius: 8,
              }}
            />
          </div>
        )
      })}
    </div>
  )
}
