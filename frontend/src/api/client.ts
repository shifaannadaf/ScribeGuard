// Single source of truth for backend base URL.
// Override at runtime by setting `VITE_API_BASE` in a .env.local file.
export const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000"

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  })
  if (!res.ok) {
    let detail = "Request failed"
    try {
      const body = await res.json()
      detail = body.detail ?? JSON.stringify(body)
    } catch {
      try { detail = await res.text() } catch { /* ignore */ }
    }
    throw new ApiError(detail, res.status)
  }
  if (res.status === 204) return undefined as T
  const ct = res.headers.get("content-type") || ""
  if (ct.includes("application/json")) return (await res.json()) as T
  return (await res.text()) as unknown as T
}

export default request
