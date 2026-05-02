import { useCallback, useEffect, useRef, useState } from "react"

/**
 * Live captions via the browser's Web Speech API.
 *
 * Runs in parallel with our MediaRecorder + backend Whisper pipeline so the
 * physician sees text appear as they speak. Browser-side only; quality is
 * lower than server-side Whisper, so this is a UX overlay only — the
 * canonical transcript still comes from the backend.
 *
 * Supported in Chrome / Edge / Safari. No-ops in Firefox (isSupported=false).
 */
export interface LiveCaption {
  /** Accumulated text from result chunks marked `isFinal`. */
  transcript: string
  /** The partial words the engine is currently refining. Re-renders rapidly. */
  interim: string
  /** Whether `SpeechRecognition` (or its webkit prefix) exists in this browser. */
  isSupported: boolean
  /** Set when the engine raised an error or was denied microphone permission. */
  error: string | null
  /** Begin streaming; safe to call when already running (no-op). */
  start: () => void
  /** Stop streaming and (optionally) clear the buffer for the next session. */
  stop: (opts?: { clear?: boolean }) => void
  /** Manually clear `transcript` + `interim` (e.g. when starting a new patient). */
  reset: () => void
}

// Browsers expose either `SpeechRecognition` (standard) or
// `webkitSpeechRecognition` (Chrome/Safari). Pick whichever exists.
type SR = typeof window extends { SpeechRecognition: infer T }
  ? T
  : typeof window extends { webkitSpeechRecognition: infer T }
  ? T
  : unknown

function getRecognitionCtor(): any | null {
  if (typeof window === "undefined") return null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const w = window as any
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

export function useLiveCaption(opts?: { lang?: string }): LiveCaption {
  const lang = opts?.lang ?? "en-US"
  const [isSupported] = useState<boolean>(() => Boolean(getRecognitionCtor()))
  const [transcript, setTranscript] = useState("")
  const [interim, setInterim] = useState("")
  const [error, setError] = useState<string | null>(null)

  const recognitionRef = useRef<any>(null)
  const wantRunningRef = useRef(false)

  const buildRecognition = useCallback(() => {
    const Ctor = getRecognitionCtor()
    if (!Ctor) return null
    const r = new Ctor()
    r.continuous = true
    r.interimResults = true
    r.lang = lang

    r.onresult = (event: any) => {
      let liveInterim = ""
      let appended = ""
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i]
        const text = res[0]?.transcript ?? ""
        if (res.isFinal) appended += text
        else liveInterim += text
      }
      if (appended) {
        setTranscript(prev => (prev + " " + appended).replace(/\s+/g, " ").trim())
      }
      setInterim(liveInterim.trim())
    }

    r.onerror = (e: any) => {
      // "no-speech" fires when the user stays quiet — not really an error,
      // ignore so we don't flash a banner during pauses.
      if (e?.error === "no-speech" || e?.error === "aborted") return
      setError(e?.error ?? "speech-recognition-error")
    }

    r.onend = () => {
      // The engine auto-stops after silence even with continuous=true. If the
      // caller still wants captions, restart it.
      if (wantRunningRef.current) {
        try {
          r.start()
        } catch {
          /* already started — ignore */
        }
      }
    }

    return r
  }, [lang])

  const start = useCallback(() => {
    if (!isSupported) return
    if (wantRunningRef.current) return
    setError(null)
    setInterim("")
    if (!recognitionRef.current) {
      recognitionRef.current = buildRecognition()
    }
    wantRunningRef.current = true
    try {
      recognitionRef.current?.start()
    } catch {
      /* "already started" — fine */
    }
  }, [buildRecognition, isSupported])

  const stop = useCallback((stopOpts?: { clear?: boolean }) => {
    wantRunningRef.current = false
    try {
      recognitionRef.current?.stop()
    } catch {
      /* not running */
    }
    setInterim("")
    if (stopOpts?.clear) setTranscript("")
  }, [])

  const reset = useCallback(() => {
    setTranscript("")
    setInterim("")
    setError(null)
  }, [])

  // Tear down on unmount
  useEffect(() => {
    return () => {
      wantRunningRef.current = false
      try { recognitionRef.current?.abort() } catch { /* noop */ }
      recognitionRef.current = null
    }
  }, [])

  return { transcript, interim, isSupported, error, start, stop, reset }
}
