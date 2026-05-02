/**
 * Patient-context sidebar — renders the OpenMRS chart snapshot taken on
 * intake (or refreshed on demand). Everything shown here is fetched live
 * from the OpenMRS sandbox — no fallbacks, no demo data.
 */
import { useState } from 'react'
import { RefreshCw, User, Pill, ShieldOff, Stethoscope, ClipboardList } from 'lucide-react'
import type { PatientContextSnapshot } from '../api/encounters'
import { refreshPatientContext } from '../api/encounters'

interface Props {
  encounterId: string
  snapshot: PatientContextSnapshot | null
  onRefreshed: () => void
}

export default function PatientContextPanel({ encounterId, snapshot, onRefreshed }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    setBusy(true); setError(null)
    try {
      await refreshPatientContext(encounterId)
      onRefreshed()
    } catch (e: any) {
      setError(e?.message ?? 'Could not refresh OpenMRS context')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 12,
      padding: 14,
      background: 'var(--bg-surface, #1a1c25)',
      border: '1px solid var(--border-color, #2a2d3a)',
      borderRadius: 12,
      minWidth: 280,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <User size={16} />
        <strong>OpenMRS chart context</strong>
        <button onClick={refresh} disabled={busy}
          style={{
            marginLeft: 'auto',
            padding: '4px 8px', borderRadius: 999, fontSize: 11,
            background: 'transparent', border: '1px solid var(--border-color, #2a2d3a)',
            color: '#9ca3af', cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 4,
          }}>
          <RefreshCw size={11} /> {busy ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div style={{ fontSize: 12, color: '#fca5a5' }}>{error}</div>
      )}

      {!snapshot && (
        <div style={{ fontSize: 12, color: '#9ca3af' }}>
          No OpenMRS snapshot yet. Click <em>Refresh</em> to query the patient's chart.
        </div>
      )}

      {snapshot && (
        <>
          <div style={{ fontSize: 11, color: '#9ca3af' }}>
            Snapshot @ {new Date(snapshot.fetched_at).toLocaleString()}
            {snapshot.patient_uuid && (
              <> · Patient/<code>{snapshot.patient_uuid.slice(0, 8)}</code>…</>
            )}
          </div>

          {snapshot.patient_demographics && (
            <Section title="Demographics" icon={<User size={13} />}>
              <Demographics demographics={snapshot.patient_demographics} />
            </Section>
          )}

          <Section title={`Active medications (${(snapshot.existing_medications || []).length})`} icon={<Pill size={13} />}>
            <ResourceRows
              empty="No existing medication requests."
              items={(snapshot.existing_medications || []).map(r => ({
                primary: deepText(r, ['medicationCodeableConcept', 'text']) || deepText(r, ['medicationReference', 'display']) || '(unnamed)',
                secondary: deepText(r, ['dosageInstruction', 0, 'text']) || '',
                tail: r.status as string | undefined,
              }))}
            />
          </Section>

          <Section title={`Known allergies (${(snapshot.existing_allergies || []).length})`} icon={<ShieldOff size={13} />}>
            <ResourceRows
              empty="No documented allergies."
              items={(snapshot.existing_allergies || []).map(r => ({
                primary: deepText(r, ['code', 'text']) || '(unnamed)',
                secondary: deepText(r, ['reaction', 0, 'manifestation', 0, 'text']) || '',
                tail: deepText(r, ['reaction', 0, 'severity']),
              }))}
            />
          </Section>

          <Section title={`Conditions (${(snapshot.existing_conditions || []).length})`} icon={<Stethoscope size={13} />}>
            <ResourceRows
              empty="No active conditions."
              items={(snapshot.existing_conditions || []).map(r => ({
                primary: deepText(r, ['code', 'text']) || '(unnamed)',
                secondary: deepText(r, ['clinicalStatus', 'text']) || '',
                tail: deepText(r, ['verificationStatus', 'text']),
              }))}
            />
          </Section>

          <Section title={`Recent encounters (${(snapshot.recent_encounters || []).length})`} icon={<ClipboardList size={13} />}>
            <ResourceRows
              empty="No prior encounters."
              items={(snapshot.recent_encounters || []).slice(0, 8).map(r => ({
                primary: deepText(r, ['period', 'start']) || '(no date)',
                secondary: deepText(r, ['class', 'display']) || (r.status as string) || '',
                tail: '',
              }))}
            />
          </Section>

          {snapshot.fetch_errors && Object.keys(snapshot.fetch_errors).length > 0 && (
            <div style={{ fontSize: 11, color: '#fca5a5' }}>
              <strong>Fetch errors:</strong> {Object.entries(snapshot.fetch_errors).map(([k, v]) => `${k}: ${v}`).join(' · ')}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontSize: 11, fontWeight: 700, color: '#cbd5e1', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        {icon} {title}
      </span>
      {children}
    </div>
  )
}

function Demographics({ demographics }: { demographics: Record<string, unknown> }) {
  const ids = ((demographics as any)?.identifiers || []) as Array<{ system?: string; value?: string }>
  return (
    <div style={{ fontSize: 12, color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: 2 }}>
      <span><strong>{(demographics as any)?.name ?? '(no name)'}</strong></span>
      <span style={{ color: '#9ca3af' }}>
        {(demographics as any)?.gender ?? '—'}
        {(demographics as any)?.birth_date ? ` · DOB ${(demographics as any).birth_date}` : ''}
      </span>
      {ids.slice(0, 3).map((i, ix) => (
        <code key={ix} style={{ fontSize: 10, color: '#9ca3af' }}>{i.value}</code>
      ))}
    </div>
  )
}

function ResourceRows({ items, empty }: { items: Array<{ primary: string; secondary: string; tail?: string }>; empty: string }) {
  if (items.length === 0) return <div style={{ fontSize: 12, color: '#9ca3af' }}>{empty}</div>
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {items.map((it, i) => (
        <div key={i} style={{
          display: 'grid', gridTemplateColumns: '1fr auto', gap: 6,
          padding: '6px 8px', borderRadius: 6,
          background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color, #2a2d3a)',
          fontSize: 12,
        }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <strong style={{ fontSize: 12 }}>{it.primary}</strong>
            {it.secondary && <span style={{ fontSize: 11, color: '#9ca3af' }}>{it.secondary}</span>}
          </div>
          {it.tail && <span style={{ fontSize: 10, color: '#9ca3af' }}>{it.tail}</span>}
        </div>
      ))}
    </div>
  )
}

// Safely walk a possibly-missing path through a JSON object
function deepText(obj: unknown, path: Array<string | number>): string | undefined {
  let cur: any = obj
  for (const k of path) {
    if (cur == null) return undefined
    cur = cur[k as any]
  }
  if (cur == null) return undefined
  if (typeof cur === 'string') return cur
  if (typeof cur === 'number' || typeof cur === 'boolean') return String(cur)
  return undefined
}
