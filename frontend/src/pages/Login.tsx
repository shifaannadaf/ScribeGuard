import { useNavigate } from 'react-router-dom'
import './Login.css'

export default function Login() {
  const navigate = useNavigate()

  return (
    <div className="login-container">
      <div className="login-card">

        <div className="login-header">
          <div className="login-logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </svg>
          </div>
          <h1 className="login-title">ScribeGuard</h1>
        </div>

        <p className="login-subtitle">
          AI-powered clinical documentation.<br />
          Record. Transcribe. Review. Submit.
        </p>

        <div className="login-divider" />

        <button
          onClick={() => navigate('/dashboard')}
          className="login-btn"
        >
          Continue as Guest
        </button>

        <p className="login-footer">
          For authorized medical personnel only. All sessions are logged.
        </p>

      </div>
    </div>
  )
}
