// DEPRECATED — this page has been replaced by EncounterWorkspace.
// Kept to preserve any deep links; the route redirects via App.tsx.
import { useParams, Navigate } from 'react-router-dom'

export default function NoteDetail() {
  const { id } = useParams<{ id: string }>()
  return <Navigate to={`/encounters/${id}`} replace />
}
