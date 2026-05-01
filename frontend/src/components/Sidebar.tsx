import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Clock, Moon, Sun, Activity } from 'lucide-react'
import './Sidebar.css'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/history',   label: 'Encounters', icon: Clock },
]

export default function Sidebar() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('theme') as 'light' | 'dark') || 'dark'
  })

  useEffect(() => {
    if (theme === 'light') document.body.classList.add('light')
    else                   document.body.classList.remove('light')
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'light' ? 'dark' : 'light')

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo-container">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="22" />
          </svg>
        </div>
        <span className="sidebar-title">ScribeGuard</span>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <Icon size={18} className="nav-icon" />
            {label}
          </NavLink>
        ))}
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="nav-link"
        >
          <Activity size={18} className="nav-icon" />
          Agent API Docs
        </a>
      </nav>

      <div style={{ marginTop: 'auto', padding: '1rem' }}>
        <button onClick={toggleTheme} className="nav-link" style={{ width: '100%', justifyContent: 'flex-start' }}>
          {theme === 'dark' ? (
            <><Sun size={18} className="nav-icon" /> Light Mode</>
          ) : (
            <><Moon size={18} className="nav-icon" /> Dark Mode</>
          )}
        </button>
      </div>
    </aside>
  )
}
