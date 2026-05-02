import { useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Pencil, Eye, CheckCheck, Upload, X, RotateCcw, Bot, Loader2, Users, UserPlus, User, ChevronDown } from 'lucide-react'
import {
  listEncounters, approveEncounter, revertEncounter, pushToOpenMRS,
  type EncounterListItem, type EncounterStatus,
} from '../api/encounters'
import { searchPatients, type OpenMRSPatient } from '../api/openmrs'

type Filter = 'All Statuses' | 'Pending Review' | 'Approved' | 'In OpenMRS'
type GroupedEncounters = Record<string, EncounterListItem[]>

const filters: Filter[] = ['All Statuses', 'Pending Review', 'Approved', 'In OpenMRS']

const statusMap: Record<EncounterStatus, { label: string; style: string }> = {
  pending:  { label: 'Pending Review', style: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' },
  approved: { label: 'Approved',       style: 'bg-green-500/10 text-green-400 border border-green-500/20' },
  pushed:   { label: 'In OpenMRS',     style: 'bg-blue-500/10 text-blue-400 border border-blue-500/20' },
}

const filterActiveStyle: Record<Filter, string> = {
  'All Statuses':  'bg-gray-700 text-white border-gray-600',
  'Pending Review':'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  'Approved':      'bg-green-500/10 text-green-400 border-green-500/20',
  'In OpenMRS':    'bg-blue-500/10 text-blue-400 border-blue-500/20',
}

const filterToStatus: Record<Filter, EncounterStatus | undefined> = {
  'All Statuses':  undefined,
  'Pending Review': 'pending',
  'Approved':       'approved',
  'In OpenMRS':     'pushed',
}

function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="relative group/tip">
      {children}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-700 text-white text-xs rounded-md whitespace-nowrap opacity-0 group-hover/tip:opacity-100 transition-opacity duration-150 pointer-events-none z-10">
        {label}
        <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-700" />
      </div>
    </div>
  )
}

function ConfirmModal({ record, onConfirm, onCancel }: {
  record: EncounterListItem; onConfirm: () => void; onCancel: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-sm mx-4 shadow-xl">
        <div className="flex items-start justify-between mb-4">
          <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center shrink-0">
            <CheckCheck size={20} className="text-green-400" />
          </div>
          <button onClick={onCancel} className="text-gray-600 hover:text-white transition-colors cursor-pointer"><X size={18} /></button>
        </div>
        <h2 className="text-white text-base font-semibold mb-1">Approve Note</h2>
        <p className="text-gray-400 text-sm mb-1">You are approving the note for <span className="text-white font-medium">{record.patient_name}</span>.</p>
        <p className="text-gray-500 text-xs mb-6">{record.patient_id} · {record.date} · {record.time}</p>
        <p className="text-gray-400 text-sm mb-6">This confirms you have reviewed the AI-generated content and it is clinically accurate.</p>
        <div className="flex gap-3">
          <button onClick={onCancel} className="flex-1 px-4 py-2.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 text-sm font-medium transition-colors duration-150 cursor-pointer">Cancel</button>
          <button onClick={onConfirm} className="flex-1 px-4 py-2.5 rounded-lg bg-green-600 hover:bg-green-500 text-white text-sm font-medium transition-colors duration-150 cursor-pointer">Approve</button>
        </div>
      </div>
    </div>
  )
}

function RevertModal({ record, onConfirm, onCancel }: {
  record: EncounterListItem; onConfirm: () => void; onCancel: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-sm mx-4 shadow-xl">
        <div className="flex items-start justify-between mb-4">
          <div className="w-10 h-10 rounded-full bg-yellow-500/10 flex items-center justify-center shrink-0">
            <RotateCcw size={20} className="text-yellow-400" />
          </div>
          <button onClick={onCancel} className="text-gray-600 hover:text-white transition-colors cursor-pointer"><X size={18} /></button>
        </div>
        <h2 className="text-white text-base font-semibold mb-1">Revert Approval</h2>
        <p className="text-gray-400 text-sm mb-1">You are reverting the approval for <span className="text-white font-medium">{record.patient_name}</span>.</p>
        <p className="text-gray-500 text-xs mb-6">{record.patient_id} · {record.date} · {record.time}</p>
        <p className="text-gray-400 text-sm mb-6">This will move the note back to <span className="text-yellow-400 font-medium">Pending Review</span>.</p>
        <div className="flex gap-3">
          <button onClick={onCancel} className="flex-1 px-4 py-2.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 text-sm font-medium transition-colors duration-150 cursor-pointer">Cancel</button>
          <button onClick={onConfirm} className="flex-1 px-4 py-2.5 rounded-lg bg-yellow-600 hover:bg-yellow-500 text-white text-sm font-medium transition-colors duration-150 cursor-pointer">Revert</button>
        </div>
      </div>
    </div>
  )
}

function PatientSearchModal({ record, onConfirm, onCancel }: {
  record: EncounterListItem; onConfirm: (patientUuid: string | null) => void; onCancel: () => void
}) {
  const [query, setQuery] = useState(record.patient_name)
  const [searching, setSearching] = useState(false)
  const [patients, setPatients] = useState<OpenMRSPatient[]>([])
  const [searched, setSearched] = useState(false)
  const [selectedPatient, setSelectedPatient] = useState<OpenMRSPatient | null>(null)

  async function handleSearch() {
    if (!query.trim()) return
    setSearching(true)
    try {
      const results = await searchPatients(query)
      setPatients(results)
      setSearched(true)
      if (results.length === 1) {
        setSelectedPatient(results[0])
      }
    } catch (e: any) {
      alert(`Search failed: ${e.message}`)
    } finally {
      setSearching(false)
    }
  }

  function handleConfirm() {
    if (selectedPatient) {
      onConfirm(selectedPatient.uuid)
    } else if (searched && patients.length === 0) {
      // Create new patient
      onConfirm(null)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md mx-4 shadow-xl">
        <div className="flex items-start justify-between mb-4">
          <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center shrink-0">
            <Upload size={20} className="text-blue-400" />
          </div>
          <button onClick={onCancel} className="text-gray-600 hover:text-white transition-colors cursor-pointer">
            <X size={18} />
          </button>
        </div>
        
        <h2 className="text-white text-base font-semibold mb-1">Push to OpenMRS</h2>
        <p className="text-gray-400 text-sm mb-1">
          Pushing note for <span className="text-white font-medium">{record.patient_name}</span>
        </p>
        <p className="text-gray-500 text-xs mb-5">{record.patient_id} · {record.date} · {record.time}</p>

        <label className="text-gray-500 text-xs font-medium uppercase tracking-wider block mb-1.5">
          Search for patient in OpenMRS
        </label>
        
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Enter patient name or ID..."
            className="flex-1 bg-gray-800 border border-gray-700 text-gray-200 placeholder-gray-600 text-sm rounded-lg px-3 py-2.5 outline-none focus:border-blue-600 transition-colors duration-150"
          />
          <button
            onClick={handleSearch}
            disabled={searching || !query.trim()}
            className="px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors duration-150 cursor-pointer flex items-center gap-2"
          >
            {searching ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Search
          </button>
        </div>

        {searched && (
          <div className="mb-4">
            {patients.length === 0 ? (
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-yellow-500/10 flex items-center justify-center shrink-0 mt-0.5">
                    <UserPlus size={16} className="text-yellow-400" />
                  </div>
                  <div className="flex-1">
                    <p className="text-white text-sm font-medium mb-1">Patient not found</p>
                    <p className="text-gray-400 text-xs">
                      No patient found with "{query}". A new patient record will be created in OpenMRS.
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2 mb-2">
                  <Users size={14} className="text-gray-500" />
                  <p className="text-gray-500 text-xs font-medium uppercase tracking-wider">
                    Found {patients.length} patient{patients.length !== 1 ? 's' : ''}
                  </p>
                </div>
                {patients.map(patient => (
                  <button
                    key={patient.uuid}
                    onClick={() => setSelectedPatient(patient)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors duration-150 cursor-pointer ${
                      selectedPatient?.uuid === patient.uuid
                        ? 'bg-blue-500/10 border-blue-500/30 text-white'
                        : 'bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-600'
                    }`}
                  >
                    <p className="text-sm font-medium mb-0.5">{patient.name}</p>
                    <p className="text-xs text-gray-500">
                      ID: {patient.identifier}
                      {patient.birthdate && ` · DOB: ${patient.birthdate}`}
                      {patient.gender && ` · ${patient.gender.toUpperCase()}`}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 text-sm font-medium transition-colors duration-150 cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!searched || (patients.length > 1 && !selectedPatient)}
            className="flex-1 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors duration-150 cursor-pointer"
          >
            {searched && patients.length === 0 ? 'Create & Push' : 'Push'}
          </button>
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
  const [searchPatientRecord, setSearchPatientRecord] = useState<EncounterListItem | null>(null)
  const [pushingRecord, setPushingRecord] = useState<string | null>(null)
  const [expandedPatients, setExpandedPatients] = useState<Record<string, boolean>>({})
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

  function groupEncountersByPatient(encounters: EncounterListItem[]): GroupedEncounters {
    const grouped: GroupedEncounters = {}
    encounters.forEach(enc => {
      const key = `${enc.patient_name}|${enc.patient_id}`
      if (!grouped[key]) grouped[key] = []
      grouped[key].push(enc)
    })
    // Sort encounters within each group by date (newest first)
    Object.keys(grouped).forEach(key => {
      grouped[key].sort((a, b) => {
        const dateA = new Date(`${a.date} ${a.time}`).getTime()
        const dateB = new Date(`${b.date} ${b.time}`).getTime()
        return dateB - dateA
      })
    })
    return grouped
  }

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

  async function handlePushConfirm(patientUuid: string | null) {
    if (!searchPatientRecord) return
    
    setPushingRecord(searchPatientRecord.id)
    setSearchPatientRecord(null)
    
    try {
      await pushToOpenMRS(searchPatientRecord.id, patientUuid || '')
      alert('Successfully pushed to OpenMRS!')
      fetchRecords()
    } catch (e: any) {
      alert(`Error: ${e.message}`)
    } finally {
      setPushingRecord(null)
    }
  }

  return (
    <div className="p-8">
      <h1 className="text-white text-2xl font-semibold mb-1">History</h1>
      <p className="text-gray-500 text-sm mb-6">All patient encounter transcriptions.</p>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Search by patient name or ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-gray-900 border border-gray-800 text-gray-200 placeholder-gray-600 text-sm rounded-lg pl-9 pr-4 py-2.5 outline-none focus:border-blue-600 transition-colors duration-150"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {filters.map(f => (
            <button
              key={f}
              onClick={() => setActiveFilter(f)}
              className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors duration-150 cursor-pointer ${
                activeFilter === f ? filterActiveStyle[f] : 'bg-gray-900 text-gray-500 border-gray-800 hover:border-gray-600 hover:text-gray-300'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center mt-24 gap-2 text-gray-500">
          <Loader2 size={18} className="animate-spin" />
          <span className="text-sm">Loading encounters...</span>
        </div>
      )}

      {error && <p className="text-red-400 text-sm text-center mt-24">{error}</p>}

      {!loading && !error && (
        <div className="flex flex-col gap-3">
          {records.length === 0 && (
            <p className="text-gray-600 text-sm text-center mt-24">No encounters match your search.</p>
          )}
          
          {(() => {
            const grouped = groupEncountersByPatient(records)
            const groups = Object.entries(grouped)
            
            return groups.map(([patientKey, patientEncounters]) => {
              const [patientName, patientId] = patientKey.split('|')
              const isExpanded = expandedPatients[patientKey]
              const hasMultipleVisits = patientEncounters.length > 1
              
              return (
                <div key={patientKey} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                  {/* Patient Name Row */}
                  <div 
                    className="px-5 py-4 flex items-center justify-between cursor-pointer hover:bg-gray-800/30 transition-colors"
                    onClick={() => hasMultipleVisits && setExpandedPatients(prev => ({ ...prev, [patientKey]: !prev[patientKey] }))}
                  >
                    <div className="flex items-center gap-3 flex-1">
                      <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center">
                        <User size={16} className="text-blue-400" />
                      </div>
                      <div>
                        <h3 className="text-white font-medium text-base">{patientName}</h3>
                        <p className="text-gray-500 text-xs">{patientId}{hasMultipleVisits ? ` · ${patientEncounters.length} visits` : ''}</p>
                      </div>
                    </div>
                    {hasMultipleVisits && (
                      <ChevronDown size={18} className={`text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} />
                    )}
                  </div>
                  
                  {/* Visits - Show all if expanded OR single visit always */}
                  {(isExpanded || !hasMultipleVisits) && (
                    <div className="border-t border-gray-800">
                      {patientEncounters.map((record, idx) => {
                        const { label, style } = statusMap[record.status]
                        const canApprove = record.status === 'pending'
                        return (
                          <div key={record.id} className="px-5 py-4 flex items-center gap-4 hover:bg-gray-800/20 transition-colors border-b border-gray-800 last:border-b-0">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-3 mb-1">
                                {hasMultipleVisits && (
                                  <span className="text-gray-400 text-xs font-medium">Visit {patientEncounters.length - idx}</span>
                                )}
                                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style}`}>{label}</span>
                              </div>
                              <p className="text-gray-500 text-xs truncate mb-1">{record.snippet}</p>
                              <div className="flex items-center gap-3 text-gray-600 text-xs">
                                <span>{record.date}</span><span>·</span>
                                <span>{record.time}</span>
                                {record.duration && <><span>·</span><span>{record.duration}</span></>}
                              </div>
                            </div>
                            <div className="flex items-center gap-1 shrink-0">
                              <Tooltip label="Edit Note">
                                <button onClick={() => navigate(`/notes/${record.id}`)} className="p-2 text-gray-500 hover:text-white hover:bg-gray-800 rounded-lg transition-colors duration-150 cursor-pointer">
                                  <Pencil size={16} />
                                </button>
                              </Tooltip>
                              <Tooltip label="View Transcript">
                                <button onClick={() => navigate(`/notes/${record.id}?mode=view`)} className="p-2 text-gray-500 hover:text-white hover:bg-gray-800 rounded-lg transition-colors duration-150 cursor-pointer">
                                  <Eye size={16} />
                                </button>
                              </Tooltip>
                              <Tooltip label="AI Assistant">
                                <button onClick={() => navigate(`/notes/${record.id}/ai`)} className="p-2 text-gray-500 hover:text-blue-400 hover:bg-gray-800 rounded-lg transition-colors duration-150 cursor-pointer">
                                  <Bot size={16} />
                                </button>
                              </Tooltip>
                              <Tooltip label={canApprove ? 'Approve Note' : 'Already Approved'}>
                                <button onClick={() => canApprove && setConfirmRecord(record)} className={`p-2 rounded-lg transition-colors duration-150 ${canApprove ? 'text-gray-500 hover:text-green-400 hover:bg-gray-800 cursor-pointer' : 'text-gray-700 cursor-not-allowed'}`}>
                                  <CheckCheck size={16} />
                                </button>
                              </Tooltip>
                              {record.status === 'approved' && (
                                <Tooltip label="Revert Approval">
                                  <button onClick={() => setRevertRecord(record)} className="p-2 text-gray-500 hover:text-yellow-400 hover:bg-gray-800 rounded-lg transition-colors duration-150 cursor-pointer">
                                    <RotateCcw size={16} />
                                  </button>
                                </Tooltip>
                              )}
                              <Tooltip label="Push to OpenMRS">
                                <button 
                                  onClick={() => record.status === 'approved' && setSearchPatientRecord(record)} 
                                  disabled={record.status !== 'approved' || pushingRecord === record.id}
                                  className={`p-2 rounded-lg transition-colors duration-150 ${
                                    record.status === 'approved' && pushingRecord !== record.id
                                      ? 'text-gray-500 hover:text-blue-400 hover:bg-gray-800 cursor-pointer' 
                                      : 'text-gray-700 cursor-not-allowed'
                                  }`}
                                >
                                  {pushingRecord === record.id ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                                </button>
                              </Tooltip>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })
          })()}
        </div>
      )}

      {confirmRecord && <ConfirmModal record={confirmRecord} onConfirm={() => handleApprove(confirmRecord.id)} onCancel={() => setConfirmRecord(null)} />}
      {revertRecord  && <RevertModal  record={revertRecord}  onConfirm={() => handleRevert(revertRecord.id)}   onCancel={() => setRevertRecord(null)} />}
      {searchPatientRecord && <PatientSearchModal record={searchPatientRecord} onConfirm={handlePushConfirm} onCancel={() => setSearchPatientRecord(null)} />}
    </div>
  )
}
