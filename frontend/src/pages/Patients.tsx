import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Loader2, UserRound, ChevronRight } from 'lucide-react'
import { searchPatients, type OpenMRSPatient } from '../api/openmrs'

function fmt(date: string | null) {
  if (!date) return '—'
  try {
    const d = date.includes('T') ? new Date(date) : new Date(date + 'T12:00:00')
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
  } catch { return date }
}

export default function Patients() {
  const navigate = useNavigate()
  const [query,   setQuery]   = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<OpenMRSPatient[] | null>(null)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    if (!query.trim()) {
      setResults(null)
      setError(null)
      return
    }

    const timer = setTimeout(async () => {
      setLoading(true)
      setError(null)
      try {
        const patients = await searchPatients(query.trim())
        if (patients.length === 0) {
          setResults([])
          setError(`No patients found for "${query.trim()}"`)
        } else {
          setResults(patients)
        }
      } catch {
        setError('Could not reach OpenMRS. Make sure it is running.')
      } finally {
        setLoading(false)
      }
    }, 350)

    return () => clearTimeout(timer)
  }, [query])

  return (
    <div className="flex flex-col h-full px-8 py-8 overflow-y-auto">

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-white text-2xl font-semibold mb-1">Patients</h1>
        <p className="text-gray-500 text-sm">Search by name or OpenMRS ID to load a patient profile.</p>
      </div>

      {/* Search bar */}
      <div className="relative max-w-xl mb-6">
        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
          {loading
            ? <Loader2 size={16} className="text-gray-500 animate-spin" />
            : <Search size={16} className="text-gray-500" />}
        </div>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search by name or ID (e.g. Atharv or 10001PE)"
          autoFocus
          className="w-full bg-gray-900 border border-gray-700 text-gray-200 placeholder-gray-600 text-sm rounded-xl pl-10 pr-4 py-3 outline-none focus:border-blue-600 transition-colors duration-150"
        />
      </div>

      {/* Error */}
      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {/* Results */}
      {results && results.length > 0 && (
        <div className="flex flex-col gap-2 max-w-xl">
          <p className="text-gray-500 text-xs mb-1">{results.length} patient{results.length !== 1 ? 's' : ''} found</p>
          {results.map(p => (
            <button
              key={p.uuid}
              onClick={() => navigate(`/patients/${p.uuid}`, { state: { patient: p } })}
              className="bg-gray-900 border border-gray-800 hover:border-blue-600/50 rounded-xl px-4 py-3.5 flex items-center gap-4 text-left transition-colors duration-150 cursor-pointer group"
            >
              <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center shrink-0">
                <UserRound size={18} className="text-blue-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium">{p.name}</p>
                <p className="text-gray-500 text-xs mt-0.5">
                  {p.identifier}
                  {p.gender && <span className="mx-1.5">·</span>}
                  {p.gender?.toUpperCase()}
                  {p.birthdate && <span className="mx-1.5">·</span>}
                  {fmt(p.birthdate)}
                  {p.address && <span className="mx-1.5">·</span>}
                  {p.address}
                </p>
              </div>
              <ChevronRight size={16} className="text-gray-600 group-hover:text-blue-400 transition-colors shrink-0" />
            </button>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!results && !loading && (
        <div className="flex flex-col items-center justify-center flex-1 gap-3 text-center">
          <div className="w-14 h-14 rounded-2xl bg-gray-800 flex items-center justify-center">
            <UserRound size={26} className="text-gray-600" />
          </div>
          <p className="text-gray-600 text-sm">Search for a patient to get started</p>
        </div>
      )}

    </div>
  )
}
