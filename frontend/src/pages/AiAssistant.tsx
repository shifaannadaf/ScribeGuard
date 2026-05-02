// DEPRECATED — the legacy AI assistant chat has been folded into the
// EncounterWorkspace. Route preserved for any in-flight deep links.
import { useParams, Navigate } from 'react-router-dom'

export default function AiAssistant() {
  const { id } = useParams<{ id: string }>()
  return <Navigate to={`/encounters/${id}`} replace />
}
