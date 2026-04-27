import { useState, useRef, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, Bot, User, Loader2 } from 'lucide-react'
import { sendChatMessage, getEncounter, type EncounterDetail, type ChatMessage as APIChatMessage } from '../api/encounters'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
}

export default function AiAssistant() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [record, setRecord] = useState<EncounterDetail | null>(null)

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!id) return
    getEncounter(id).then(data => {
      setRecord(data)
      setMessages([{
        id: 0,
        role: 'assistant',
        content: `Hi, I am the ScribeGuard assistant for this encounter. I have read the full transcript for **${data.patient_name}**.\n\nAsk me anything about the consultation — medications, diagnoses, the care plan, or request a summary.`,
      }])
    })
  }, [id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend() {
    const text = input.trim()
    if (!text || loading || !id) return

    const userMsg: Message = { id: Date.now(), role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    const history: APIChatMessage[] = messages
      .filter(m => m.id !== 0)
      .map(m => ({ role: m.role, content: m.content }))

    try {
      const res = await sendChatMessage(id, text, history)
      setMessages(prev => [...prev, { id: res.message_id, role: 'assistant', content: res.reply }])
    } catch {
      setMessages(prev => [...prev, { id: Date.now(), role: 'assistant', content: 'Sorry, something went wrong. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!record) {
    return (
      <div className="flex items-center justify-center h-screen gap-2 text-gray-500">
        <Loader2 size={18} className="animate-spin" /><span className="text-sm">Loading...</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen">

      {/* Header */}
      <div className="px-8 py-5 border-b border-gray-800 flex items-center gap-4 shrink-0">
        <button
          onClick={() => navigate(-1)}
          className="p-1.5 text-gray-500 hover:text-white hover:bg-gray-800 rounded-lg transition-colors duration-150 cursor-pointer"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="w-8 h-8 rounded-lg bg-blue-600/20 flex items-center justify-center shrink-0">
          <Bot size={16} className="text-blue-400" />
        </div>
        <div className="flex-1">
          <h1 className="text-white text-base font-semibold leading-tight">AI Assistant</h1>
          <p className="text-gray-500 text-xs mt-0.5">{record.patient_name} · {record.patient_id} · {record.date}</p>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
          Grounded in transcript
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-8 py-6 flex flex-col gap-5">
        {messages.map(msg => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>

            <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
              msg.role === 'assistant' ? 'bg-blue-600/20' : 'bg-gray-700'
            }`}>
              {msg.role === 'assistant'
                ? <Bot size={14} className="text-blue-400" />
                : <User size={14} className="text-gray-400" />
              }
            </div>

            <div className={`max-w-xl px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
              msg.role === 'assistant'
                ? 'bg-gray-900 border border-gray-800 text-gray-200 rounded-tl-sm'
                : 'bg-blue-600 text-white rounded-tr-sm'
            }`}>
              {msg.content}
            </div>

          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-blue-600/20 flex items-center justify-center shrink-0 mt-0.5">
              <Bot size={14} className="text-blue-400" />
            </div>
            <div className="bg-gray-900 border border-gray-800 px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-2">
              <Loader2 size={14} className="text-blue-400 animate-spin" />
              <span className="text-gray-500 text-sm">Thinking...</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Suggested prompts */}
      {messages.length === 1 && (
        <div className="px-8 pb-4 flex flex-wrap gap-2">
          {[
            'Summarize this encounter',
            'What medications were mentioned?',
            'What is the diagnosis?',
            'What is the care plan?',
          ].map(prompt => (
            <button
              key={prompt}
              onClick={() => { setInput(prompt); }}
              className="text-xs px-3 py-1.5 rounded-full border border-gray-700 text-gray-400 hover:border-blue-600 hover:text-blue-400 transition-colors duration-150 cursor-pointer"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-8 pb-6 pt-2 shrink-0">
        <div className="flex items-end gap-3 bg-gray-900 border border-gray-800 focus-within:border-blue-600 rounded-xl px-4 py-3 transition-colors duration-150">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about medications, diagnoses, the care plan…"
            rows={1}
            className="flex-1 bg-transparent text-gray-200 placeholder-gray-600 text-sm outline-none resize-none leading-relaxed"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="p-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-30 disabled:cursor-not-allowed text-white transition-colors duration-150 cursor-pointer shrink-0"
          >
            <Send size={15} />
          </button>
        </div>
        <p className="text-gray-600 text-xs mt-2 text-center">Responses are AI-generated based on the transcript. Always verify clinically.</p>
      </div>

    </div>
  )
}
