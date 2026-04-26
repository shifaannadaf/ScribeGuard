import { useNavigate } from 'react-router-dom'

export default function Login() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-4">
      <div className="flex flex-col items-center gap-6 max-w-md w-full">

        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </svg>
          </div>
          <h1 className="text-4xl font-bold text-white tracking-tight">ScribeGuard</h1>
        </div>

        <p className="text-gray-400 text-center text-lg leading-relaxed">
          AI-powered clinical documentation.<br />
          Record. Transcribe. Review. Submit.
        </p>

        <div className="w-full border-t border-gray-800 my-2" />

        <button
          onClick={() => navigate('/dashboard')}
          className="w-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-semibold text-base py-3 px-6 rounded-xl transition-colors duration-150 cursor-pointer"
        >
          Continue as Guest
        </button>

        <p className="text-gray-600 text-sm text-center">
          For authorized medical personnel only. All sessions are logged.
        </p>

      </div>
    </div>
  )
}
