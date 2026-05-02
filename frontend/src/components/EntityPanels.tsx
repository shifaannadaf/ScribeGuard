/**
 * Entity panels rendered on the EncounterWorkspace.
 *
 * Each panel mirrors a real OpenMRS / FHIR resource type:
 *   - AllergyPanel   → AllergyIntolerance
 *   - ConditionPanel → Condition
 *   - VitalsPanel    → Observation (vital-signs)
 *   - FollowUpPanel  → free text + future CarePlan
 */
import { AlertTriangle, Activity, Heart, CalendarClock, ShieldOff, Stethoscope } from 'lucide-react'
import type { Allergy, Condition, FollowUp, VitalSign } from '../api/encounters'

const SECTION_STYLE: React.CSSProperties = {
  padding: 14,
  background: 'var(--bg-surface, #1a1c25)',
  border: '1px solid var(--border-color, #2a2d3a)',
  borderRadius: 12,
}
const HEADER_STYLE: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
  fontSize: 13, fontWeight: 700, color: 'var(--text-strong, #e5e7eb)',
}
const COUNT_STYLE: React.CSSProperties = {
  marginLeft: 'auto', fontSize: 11, color: '#9ca3af',
}
const EMPTY_STYLE: React.CSSProperties = {
  fontSize: 13, color: '#9ca3af', padding: '8px 0',
}
const TONE = (c: string | null) => {
  switch ((c || '').toLowerCase()) {
    case 'high':   return { bg: 'rgba(34,197,94,0.15)',  fg: '#86efac' }
    case 'low':    return { bg: 'rgba(239,68,68,0.15)',  fg: '#fca5a5' }
    default:       return { bg: 'rgba(245,158,11,0.15)', fg: '#fcd34d' }
  }
}
const SEVERITY_TONE = (s: string | null) => {
  switch ((s || '').toLowerCase()) {
    case 'severe': return { bg: 'rgba(239,68,68,0.18)', fg: '#fca5a5' }
    case 'moderate': return { bg: 'rgba(245,158,11,0.18)', fg: '#fcd34d' }
    case 'mild': return { bg: 'rgba(99,102,241,0.18)', fg: '#a5b4fc' }
    default: return { bg: 'rgba(255,255,255,0.05)', fg: '#9ca3af' }
  }
}
const Pill: React.FC<{ tone: { bg: string; fg: string }; children: React.ReactNode }> = ({ tone, children }) => (
  <span style={{
    padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 600,
    background: tone.bg, color: tone.fg,
  }}>{children}</span>
)

export function AllergyPanel({ items }: { items: Allergy[] }) {
  return (
    <div style={SECTION_STYLE}>
      <div style={HEADER_STYLE}>
        <ShieldOff size={16} color="#fca5a5" /> Allergies (FHIR AllergyIntolerance)
        <span style={COUNT_STYLE}>{items.length}</span>
      </div>
      {items.length === 0 && <div style={EMPTY_STYLE}>No allergies extracted from this encounter.</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {items.map(a => (
          <div key={a.id} style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr auto auto auto', gap: 10, alignItems: 'center',
            padding: '8px 10px', borderRadius: 8,
            background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color, #2a2d3a)',
            fontSize: 13,
          }}>
            <strong>{a.substance}</strong>
            <span style={{ color: '#cbd5e1' }}>{a.reaction ?? '—'}</span>
            <Pill tone={SEVERITY_TONE(a.severity)}>{a.severity ?? 'unspecified'}</Pill>
            <Pill tone={TONE(a.confidence)}>{a.confidence ?? 'medium'}</Pill>
            {a.openmrs_resource_uuid
              ? <span style={{ fontSize: 10, color: '#86efac' }}>OpenMRS ✓</span>
              : <span style={{ fontSize: 10, color: '#9ca3af' }}>not yet submitted</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

export function ConditionPanel({ items }: { items: Condition[] }) {
  return (
    <div style={SECTION_STYLE}>
      <div style={HEADER_STYLE}>
        <Stethoscope size={16} color="#a5b4fc" /> Conditions / Diagnoses (FHIR Condition)
        <span style={COUNT_STYLE}>{items.length}</span>
      </div>
      {items.length === 0 && <div style={EMPTY_STYLE}>No conditions extracted from this encounter.</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {items.map(c => (
          <div key={c.id} style={{
            display: 'grid',
            gridTemplateColumns: '1.4fr 90px 90px 1fr auto auto',
            gap: 10, alignItems: 'center',
            padding: '8px 10px', borderRadius: 8,
            background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color, #2a2d3a)',
            fontSize: 13,
          }}>
            <strong>{c.description}</strong>
            <code style={{ fontSize: 11, color: '#9ca3af' }}>{c.icd10_code ?? '—'}</code>
            <code style={{ fontSize: 11, color: '#9ca3af' }}>{c.snomed_code ?? '—'}</code>
            <span style={{ fontSize: 11, color: '#cbd5e1' }}>
              {[c.clinical_status, c.verification].filter(Boolean).join(' · ') || '—'}
            </span>
            <Pill tone={TONE(c.confidence)}>{c.confidence ?? 'medium'}</Pill>
            {c.openmrs_resource_uuid
              ? <span style={{ fontSize: 10, color: '#86efac' }}>OpenMRS ✓</span>
              : <span style={{ fontSize: 10, color: '#9ca3af' }}>not yet submitted</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

const VITAL_LABEL: Record<string, string> = {
  height: 'Height', weight: 'Weight', temperature: 'Temperature',
  respiratory_rate: 'Respiratory rate', spo2: 'SpO₂', hr: 'Heart rate',
  systolic_bp: 'Systolic BP', diastolic_bp: 'Diastolic BP',
}

export function VitalsPanel({ items }: { items: VitalSign[] }) {
  return (
    <div style={SECTION_STYLE}>
      <div style={HEADER_STYLE}>
        <Heart size={16} color="#fca5a5" /> Vital signs (FHIR Observation · vital-signs)
        <span style={COUNT_STYLE}>{items.length}</span>
      </div>
      {items.length === 0 && <div style={EMPTY_STYLE}>No vital-sign measurements extracted.</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8 }}>
        {items.map(v => (
          <div key={v.id} style={{
            padding: '10px 12px', borderRadius: 8,
            background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color, #2a2d3a)',
            display: 'flex', flexDirection: 'column', gap: 2,
          }}>
            <span style={{ fontSize: 11, color: '#9ca3af' }}>{VITAL_LABEL[v.kind] ?? v.kind}</span>
            <span style={{ fontSize: 18, fontWeight: 700 }}>
              {v.value} <span style={{ fontSize: 11, fontWeight: 500, color: '#9ca3af' }}>{v.unit ?? ''}</span>
            </span>
            <span style={{ fontSize: 10, color: '#9ca3af' }}>
              {v.openmrs_resource_uuid ? 'OpenMRS ✓' : 'not yet submitted'} · {v.confidence ?? 'medium'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function FollowUpPanel({ items }: { items: FollowUp[] }) {
  return (
    <div style={SECTION_STYLE}>
      <div style={HEADER_STYLE}>
        <CalendarClock size={16} color="#a5b4fc" /> Follow-ups
        <span style={COUNT_STYLE}>{items.length}</span>
      </div>
      {items.length === 0 && <div style={EMPTY_STYLE}>No follow-up instructions extracted.</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {items.map(f => (
          <div key={f.id} style={{
            display: 'grid',
            gridTemplateColumns: '1fr auto auto',
            gap: 10, alignItems: 'center',
            padding: '8px 10px', borderRadius: 8,
            background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color, #2a2d3a)',
            fontSize: 13,
          }}>
            <span>{f.description}</span>
            <span style={{ fontSize: 11, color: '#9ca3af' }}>{f.interval ?? '—'}</span>
            <span style={{ fontSize: 11, color: '#9ca3af' }}>{f.with_provider ?? ''}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Quality indicator that tells the physician this section came from
   genuine classification, not a static template. */
export function ExtractionStatus({
  meds, allergies, conditions, vitals, followups,
}: { meds: number; allergies: number; conditions: number; vitals: number; followups: number }) {
  const total = meds + allergies + conditions + vitals + followups
  return (
    <div style={{
      display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center',
      padding: '8px 12px', borderRadius: 10,
      background: total === 0 ? 'rgba(245,158,11,0.10)' : 'rgba(99,102,241,0.10)',
      border: `1px solid ${total === 0 ? '#f59e0b44' : '#6366f155'}`,
      fontSize: 12, color: total === 0 ? '#fcd34d' : '#a5b4fc',
    }}>
      {total === 0
        ? <><AlertTriangle size={14} /> Classifier emitted nothing — verify the SOAP note has substantive content.</>
        : <><Activity size={14} /> Classified {total} entit{total === 1 ? 'y' : 'ies'} from the SOAP note &amp; transcript</>}
      <span style={{ marginLeft: 'auto' }}>
        meds: {meds} · allergies: {allergies} · conditions: {conditions} · vitals: {vitals} · follow-ups: {followups}
      </span>
    </div>
  )
}
