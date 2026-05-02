import { Outlet } from 'react-router-dom'
import { Server, User } from 'lucide-react'
import Sidebar from './Sidebar'

export default function AppLayout() {
  return (
    <div className="app-container">
      <Sidebar />
      <main className="page-content">
        <header className="global-header">
          <div className="header-left">
            <h1 className="header-title">ScribeGuard Workspace</h1>
          </div>
          <div className="header-right">
            <div className="status-badge status-pushed" style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', padding: '0.375rem 0.75rem' }}>
              <Server size={14} />
              OpenMRS Sandbox Connected
            </div>
            <div className="physician-profile">
              <div className="avatar-circle">
                <User size={16} />
              </div>
              <div className="profile-info">
                <span className="profile-name">{localStorage.getItem('doctorName') || 'Attending Physician'}</span>
                <span className="profile-role">Internal Medicine</span>
              </div>
            </div>
          </div>
        </header>
        <div className="scrollable-area">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

