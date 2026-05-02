import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, User, Calendar, Clock, Pencil, Eye, Bot, CheckCheck, Upload, RotateCcw, Loader2 } from 'lucide-react'
import {
  listEncounters, approveEncounter, revertEncounter, pushToOpenMRS,
  type EncounterListItem, type EncounterStatus,
} from '../api/encounters'

const statusMap: Record<EncounterStatus, { label: string; style: string }> = {
  pending:  { label: 'Pending Review', style: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' },
  approved: { label: 'Approved',       style: 'bg-green-500/10 text-green-400 border border-green-500/20' },
  pushed:   { label: 'In OpenMRS',     style: 'bg-blue-500/10 text-blue-400 border border-blue-500/20' },
}

export default function PatientEncounters() {
  const { patientId } = useParams<{ patientId: string }>()
  const navigate = useNavigate()
  const [encounters, setEncounters] = useState<EncounterListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pushingRecord, setPushingRecord] = useState<string | null>(null)

  async function fetchEncounters() {
    if (!patientId) return
    try {
      setLoading(true)
      const res = await listEncounters({ search: patientId })
      // Filter to only this patient's encounters
      const patientEncounters = res.data.filter(enc => enc.patient_id === patientId)
      // Sort by date, newest first
      patientEncounters.sort((a, b) => {
        const dateA = new Date(`${a.date} ${a.time}`).getTime()
        const dateB = new Date(`${b.date} ${b.time}`).getTime()
        return dateB - dateA
      })
      setEncounters(patientEncounters)
      setError(null)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchEncounters() }, [patientId])

  async function handleApprove(id: string) {
    await approveEncounter(id)
    fetchEncounters()
  }

  async function handleRevert(id: string) {
    await revertEncounter(id)
    fetchEncounters()
  }

  async function handlePush(record: EncounterListItem) {
    if (record.status !== 'approved') return
    setPushingRecord(record.id)
    
    try {
      // For now, push without specifying OpenMRS patient UUID
      // In a full implementation, you'd search for the patient first
      await pushToOpenMRS(record.id, '')
      alert('Successfully pushed to OpenMRS!')
      fetchEncounters()
    } catch (e: any) {
      alert(`Error: ${e.message}`)
    } finally {
      setPushingRecord(null)
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <button onClick={() => navigate('/history')} className="flex items-center gap-2 text-gray-500 hover:text-white text-sm mb-6 transition-colors cursor-pointer">
          <ArrowLeft size={16} /> Back to History
        </button>
        <div className="flex items-center justify-center mt-24 gap-2 text-gray-500">
          <Loader2 size={18} className="animate-spin" />
          <span className="text-sm">Loading patient data...</span>
        </div>
      </div>
    )
  }

  if (error || encounters.length === 0) {
    return (
      <div className="p-8">
        <button onClick={() => navigate('/history')} className="flex items-center gap-2 text-gray-500 hover:text-white text-sm mb-6 transition-colors cursor-pointer">
          <ArrowLeft size={16} /> Back to History
        </button>
        <p className="text-red-400 text-sm text-center mt-24">{error || 'No encounters found for this patient'}</p>
      </div>
    )
  }

  const patientName = encounters[0].patient_name
  const totalVisits = encounters.length
  const pendingCount = encounters.filter(e => e.status === 'pending').length
  const approvedCount = encounters.filter(e => e.status === 'approved').length
  const pushedCount = encounters.filter(e => e.status === 'pushed').length

  return (
    <div className="p-8">
      <button onClick={() => navigate('/history')} className="flex items-center gap-2 text-gray-500 hover:text-white text-sm mb-6 transition-colors cursor-pointer">
        <ArrowLeft size={16} /> Back to History
      </button>

      {/* Patient Header */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 mb-6">
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 rounded-full bg-blue-500/10 flex items-center justify-center shrink-0">
            <User size={28} className="text-blue-400" />
          </div>
          <div className="flex-1">
            <h1 className="text-white text-2xl font-semibold mb-1">{patientName}</h1>
            <p className="text-gray-500 text-sm mb-4">Patient ID: {patientId}</p>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gray-800 flex items-center justify-center">
                  <Calendar size={16} className="text-gray-400" />
                </div>
                <div>
                  <p className="text-white text-lg font-semibold">{totalVisits}</p>
                  <p className="text-gray-500 text-xs">Total Visits</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
                  <Clock size={16} className="text-yellow-400" />
                </div>
                <div>
                  <p className="text-white text-lg font-semibold">{pendingCount}</p>
                  <p className="text-gray-500 text-xs">Pending</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                  <CheckCheck size={16} className="text-green-400" />
                </div>
                <div>
                  <p className="text-white text-lg font-semibold">{approvedCount}</p>
                  <p className="text-gray-500 text-xs">Approved</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                  <Upload size={16} className="text-blue-400" />
                </div>
                <div>
                  <p className="text-white text-lg font-semibold">{pushedCount}</p>
                  <p className="text-gray-500 text-xs">In OpenMRS</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Encounter Timeline */}
      <div className="mb-4">
        <h2 className="text-white text-lg font-semibold mb-1">Visit History</h2>
        <p className="text-gray-500 text-sm">All encounters for this patient, newest first</p>
      </div>

      <div className="flex flex-col gap-3">
        {encounters.map((record, idx) => {
          const { label, style } = statusMap[record.status]
          const canApprove = record.status === 'pending'
          const visitNumber = totalVisits - idx
          
          return (
            <div key={record.id} className="bg-gray-900 border border-gray-800 rounded-xl px-5 py-4 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-white font-medium text-sm">Visit {visitNumber}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style}`}>{label}</span>
                </div>
                <p className="text-gray-500 text-xs truncate mb-1">{record.snippet}</p>
                <div className="flex items-center gap-3 text-gray-600 text-xs">
                  <span>{record.date}</span><span>·</span>
                  <span>{record.time}</span><span>·</span>
                  <span>{record.duration}</span>
                </div>
              </div>
              
              <div className="flex items-center gap-1 shrink-0">
                <button 
                  onClick={() => navigate(`/notes/${record.id}`)} 
                  className="p-2 text-gray-500 hover:text-white hover:bg-gray-800 rounded-lg transition-colors duration-150 cursor-pointer"
                  title="Edit Note"
                >
                  <Pencil size={16} />
                </button>
                
                <button 
                  onClick={() => navigate(`/notes/${record.id}?mode=view`)} 
                  className="p-2 text-gray-500 hover:text-white hover:bg-gray-800 rounded-lg transition-colors duration-150 cursor-pointer"
                  title="View Transcript"
                >
                  <Eye size={16} />
                </button>
                
                <button 
                  onClick={() => navigate(`/notes/${record.id}/ai`)} 
                  className="p-2 text-gray-500 hover:text-blue-400 hover:bg-gray-800 rounded-lg transition-colors duration-150 cursor-pointer"
                  title="AI Assistant"
                >
                  <Bot size={16} />
                </button>
                
                <button 
                  onClick={() => canApprove && handleApprove(record.id)} 
                  disabled={!canApprove}
                  className={`p-2 rounded-lg transition-colors duration-150 ${canApprove ? 'text-gray-500 hover:text-green-400 hover:bg-gray-800 cursor-pointer' : 'text-gray-700 cursor-not-allowed'}`}
                  title={canApprove ? 'Approve Note' : 'Already Approved'}
                >
                  <CheckCheck size={16} />
                </button>
                
                {record.status === 'approved' && (
                  <button 
                    onClick={() => handleRevert(record.id)} 
                    className="p-2 text-gray-500 hover:text-yellow-400 hover:bg-gray-800 rounded-lg transition-colors duration-150 cursor-pointer"
                    title="Revert Approval"
                  >
                    <RotateCcw size={16} />
                  </button>
                )}
                
                <button 
                  onClick={() => handlePush(record)} 
                  disabled={record.status !== 'approved' || pushingRecord === record.id}
                  className={`p-2 rounded-lg transition-colors duration-150 ${
                    record.status === 'approved' && pushingRecord !== record.id
                      ? 'text-gray-500 hover:text-blue-400 hover:bg-gray-800 cursor-pointer' 
                      : 'text-gray-700 cursor-not-allowed'
                  }`}
                  title="Push to OpenMRS"
                >
                  {pushingRecord === record.id ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
