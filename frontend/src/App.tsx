import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import NoteDetail from './pages/NoteDetail'
import AiAssistant from './pages/AiAssistant'
import Patients from './pages/Patients'
import PatientProfile from './pages/PatientProfile'
import PatientEncounters from './pages/PatientEncounters'
import AppLayout from './components/AppLayout'
import './index.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/history" element={<History />} />
          <Route path="/notes/:id" element={<NoteDetail />} />
          <Route path="/notes/:id/ai" element={<AiAssistant />} />
          <Route path="/patients" element={<Patients />} />
          <Route path="/patients/encounters/:patientId" element={<PatientEncounters />} />
          <Route path="/patients/:uuid" element={<PatientProfile />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
