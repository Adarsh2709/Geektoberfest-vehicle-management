const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function token() { return localStorage.getItem('vmi_token') }
export function saveToken(value) { localStorage.setItem('vmi_token', value) }
export function clearToken() { localStorage.removeItem('vmi_token') }

export async function api(path, options = {}) {
  const headers = { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(token() ? { Authorization: `Bearer ${token()}` } : {}), ...options.headers }
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (response.status === 204) return null
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || 'Something went wrong. Please try again.')
  return body
}

export function friendlyDate(value) {
  return value ? new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '—'
}
