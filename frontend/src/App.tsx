import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import EncounterWorkspace from './pages/EncounterWorkspace'
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
          <Route path="/encounters/:id" element={<EncounterWorkspace />} />
          {/* Backward-compat aliases for old links */}
          <Route path="/notes/:id" element={<Navigate to=".." replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
