import { useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Pencil, Eye, CheckCheck, Upload, X, RotateCcw, Bot, Loader2 } from 'lucide-react'
import {
  listEncounters, approveEncounter, revertEncounter, pushToOpenMRS,
  type EncounterListItem, type EncounterStatus,
} from '../api/encounters'
import './History.css'

type Filter = 'All Statuses' | 'Pending Review' | 'Approved' | 'In OpenMRS'

const filters: Filter[] = ['All Statuses', 'Pending Review', 'Approved', 'In OpenMRS']

const statusMap: Record<EncounterStatus, { label: string; style: string }> = {
  pending:  { label: 'Pending Review', style: 'status-pending' },
  approved: { label: 'Approved',       style: 'status-approved' },
  pushed:   { label: 'In OpenMRS',     style: 'status-pushed' },
}

const filterToStatus: Record<Filter, EncounterStatus | undefined> = {
  'All Statuses':  undefined,
  'Pending Review': 'pending',
  'Approved':       'approved',
  'In OpenMRS':     'pushed',
}

function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="tooltip-container">
      {children}
      <div className="tooltip-text">{label}</div>
    </div>
  )
}

function ConfirmModal({ record, onConfirm, onCancel }: {
  record: EncounterListItem; onConfirm: () => void; onCancel: () => void
}) {
  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <div className="modal-icon-container green">
            <CheckCheck size={20} />
          </div>
          <button onClick={onCancel} className="icon-button"><X size={18} /></button>
        </div>
        <h2 className="modal-title">Approve Note</h2>
        <div className="modal-body">
          <p>You are approving the note for <span style={{ color: 'white', fontWeight: 500 }}>{record.patient_name}</span>.</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', margin: '0.25rem 0 1rem' }}>{record.patient_id} · {record.date} · {record.time}</p>
          <p>This confirms you have reviewed the AI-generated content and it is clinically accurate.</p>
        </div>
        <div className="modal-actions">
          <button onClick={onCancel} className="btn btn-secondary">Cancel</button>
          <button onClick={onConfirm} className="btn" style={{ background: 'var(--success)', color: 'white' }}>Approve</button>
        </div>
      </div>
    </div>
  )
}

function RevertModal({ record, onConfirm, onCancel }: {
  record: EncounterListItem; onConfirm: () => void; onCancel: () => void
}) {
  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <div className="modal-icon-container yellow">
            <RotateCcw size={20} />
          </div>
          <button onClick={onCancel} className="icon-button"><X size={18} /></button>
        </div>
        <h2 className="modal-title">Revert Approval</h2>
        <div className="modal-body">
          <p>You are reverting the approval for <span style={{ color: 'white', fontWeight: 500 }}>{record.patient_name}</span>.</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', margin: '0.25rem 0 1rem' }}>{record.patient_id} · {record.date} · {record.time}</p>
          <p>This will move the note back to <span style={{ color: 'var(--warning)', fontWeight: 500 }}>Pending Review</span>.</p>
        </div>
        <div className="modal-actions">
          <button onClick={onCancel} className="btn btn-secondary">Cancel</button>
          <button onClick={onConfirm} className="btn" style={{ background: 'var(--warning)', color: 'white' }}>Revert</button>
        </div>
      </div>
    </div>
  )
}

function PushModal({ record, onConfirm, onCancel }: {
  record: EncounterListItem; onConfirm: (uuid: string) => void; onCancel: () => void
}) {
  const [uuid, setUuid] = useState('')
  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <div className="modal-icon-container blue">
            <Upload size={20} />
          </div>
          <button onClick={onCancel} className="icon-button"><X size={18} /></button>
        </div>
        <h2 className="modal-title">Push to OpenMRS</h2>
        <div className="modal-body">
          <p>Pushing note for <span style={{ color: 'white', fontWeight: 500 }}>{record.patient_name}</span>.</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', margin: '0.25rem 0 1rem' }}>{record.patient_id} · {record.date} · {record.time}</p>
          <label className="input-label">OpenMRS Patient UUID</label>
          <input
            type="text"
            value={uuid}
            onChange={e => setUuid(e.target.value)}
            placeholder="e.g. b80b4ed7-da9c-4b2f-a0b4-…"
            className="input-field"
            style={{ marginBottom: '1rem' }}
          />
        </div>
        <div className="modal-actions">
          <button onClick={onCancel} className="btn btn-secondary">Cancel</button>
          <button onClick={() => uuid.trim() && onConfirm(uuid.trim())} disabled={!uuid.trim()} className="btn btn-primary">Push</button>
        </div>
      </div>
    </div>
  )
}

export default function History() {
  const [records, setRecords] = useState<EncounterListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState<Filter>('All Statuses')
  const [confirmRecord, setConfirmRecord] = useState<EncounterListItem | null>(null)
  const [revertRecord,  setRevertRecord]  = useState<EncounterListItem | null>(null)
  const [pushRecord,    setPushRecord]    = useState<EncounterListItem | null>(null)
  const navigate = useNavigate()

  async function fetchRecords() {
    try {
      setLoading(true)
      const res = await listEncounters({
        status: filterToStatus[activeFilter],
        search: search || undefined,
      })
      setRecords(res.data)
      setError(null)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchRecords() }, [activeFilter, search])

  async function handleApprove(id: string) {
    await approveEncounter(id)
    setConfirmRecord(null)
    fetchRecords()
  }

  async function handleRevert(id: string) {
    await revertEncounter(id)
    setRevertRecord(null)
    fetchRecords()
  }

  async function handlePush(id: string, uuid: string) {
    await pushToOpenMRS(id, uuid)
    setPushRecord(null)
    fetchRecords()
  }

  return (
    <div className="history-container">
      <h1 className="history-title">History</h1>
      <p className="history-subtitle">All patient encounter transcriptions.</p>

      <div className="history-controls">
        <div className="search-wrapper">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search by patient name or ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="search-input"
          />
        </div>
        <div className="filters-wrapper">
          {filters.map(f => (
            <button
              key={f}
              onClick={() => setActiveFilter(f)}
              className={`filter-btn ${activeFilter === f ? `active-${f.split(' ')[0]}` : ''}`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: '6rem', gap: '0.5rem', color: 'var(--text-muted)' }}>
          <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
          <span style={{ fontSize: '0.875rem' }}>Loading encounters...</span>
        </div>
      )}

      {error && <p style={{ color: 'var(--danger)', fontSize: '0.875rem', textAlign: 'center', marginTop: '6rem' }}>{error}</p>}

      {!loading && !error && (
        <div className="history-list">
          {records.length === 0 && (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textAlign: 'center', marginTop: '6rem' }}>No encounters match your search.</p>
          )}
          {records.map(record => {
            const { label, style } = statusMap[record.status]
            const canApprove = record.status === 'pending'
            return (
              <div key={record.id} className="history-item">
                <div className="history-item-info">
                  <div className="history-item-header">
                    <span className="history-item-name">{record.patient_name}</span>
                    <span className="history-item-id">{record.patient_id}</span>
                    <span className={`status-badge ${style}`}>{label}</span>
                  </div>
                  <p className="history-item-snippet">{record.snippet}</p>
                  <div className="history-item-meta">
                    <span>{record.date}</span><span>·</span>
                    <span>{record.time}</span><span>·</span>
                    <span>{record.duration}</span>
                  </div>
                </div>
                <div className="history-item-actions">
                  <Tooltip label="Edit Note">
                    <button onClick={() => navigate(`/notes/${record.id}`)} className="icon-button">
                      <Pencil size={16} />
                    </button>
                  </Tooltip>
                  <Tooltip label="View Transcript">
                    <button onClick={() => navigate(`/notes/${record.id}?mode=view`)} className="icon-button">
                      <Eye size={16} />
                    </button>
                  </Tooltip>
                  <Tooltip label="AI Assistant">
                    <button onClick={() => navigate(`/notes/${record.id}/ai`)} className="icon-button">
                      <Bot size={16} />
                    </button>
                  </Tooltip>
                  <Tooltip label={canApprove ? 'Approve Note' : 'Already Approved'}>
                    <button onClick={() => canApprove && setConfirmRecord(record)} className="icon-button" style={{ color: canApprove ? 'inherit' : 'var(--text-muted)', cursor: canApprove ? 'pointer' : 'not-allowed' }}>
                      <CheckCheck size={16} />
                    </button>
                  </Tooltip>
                  {record.status === 'approved' && (
                    <Tooltip label="Revert Approval">
                      <button onClick={() => setRevertRecord(record)} className="icon-button" style={{ color: 'var(--warning)' }}>
                        <RotateCcw size={16} />
                      </button>
                    </Tooltip>
                  )}
                  <Tooltip label="Push to OpenMRS">
                    <button onClick={() => record.status === 'approved' && setPushRecord(record)} className="icon-button" style={{ color: record.status === 'approved' ? 'inherit' : 'var(--text-muted)', cursor: record.status === 'approved' ? 'pointer' : 'not-allowed' }}>
                      <Upload size={16} />
                    </button>
                  </Tooltip>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {confirmRecord && <ConfirmModal record={confirmRecord} onConfirm={() => handleApprove(confirmRecord.id)} onCancel={() => setConfirmRecord(null)} />}
      {revertRecord  && <RevertModal  record={revertRecord}  onConfirm={() => handleRevert(revertRecord.id)}   onCancel={() => setRevertRecord(null)} />}
      {pushRecord    && <PushModal    record={pushRecord}    onConfirm={(uuid) => handlePush(pushRecord.id, uuid)} onCancel={() => setPushRecord(null)} />}
    </div>
  )
}
