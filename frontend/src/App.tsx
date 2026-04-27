import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import NoteDetail from './pages/NoteDetail'
import AiAssistant from './pages/AiAssistant'
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
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
