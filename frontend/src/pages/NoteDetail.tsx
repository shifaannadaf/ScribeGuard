// DEPRECATED — this page has been replaced by EncounterWorkspace.
// Kept to preserve any deep links; the route redirects via App.tsx.
import { useParams, Navigate } from 'react-router-dom'

function PatientSearchModal({ record, onConfirm, onCancel }: {
  record: EncounterDetail; onConfirm: (patientUuid: string | null) => void; onCancel: () => void
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

export default function NoteDetail() {
  const { id } = useParams<{ id: string }>()
  return <Navigate to={`/encounters/${id}`} replace />
}
