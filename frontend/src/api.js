const API_URL = (import.meta?.env?.VITE_API_URL) || 'http://localhost:8000'

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

export function formatCost(value) {
  if (value === null || value === undefined || value === '') return '₹0.00'
  const amount = Number(value)
  return Number.isFinite(amount)
    ? `₹${amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : '₹0.00'
}


export async function uploadReceipt(recordId, file) {
  const headers = { ...(token() ? { Authorization: `Bearer ${token()}` } : {}) }
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(`${API_URL}/maintenance/${recordId}/receipt`, { method: 'POST', headers, body: form })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || 'Receipt upload failed. Please try again.')
  return body
}

export async function downloadReceipt(recordId, filename) {
  const headers = { ...(token() ? { Authorization: `Bearer ${token()}` } : {}) }
  const response = await fetch(`${API_URL}/maintenance/${recordId}/receipt`, { headers })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || 'Could not download the receipt.')
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename || `receipt-${recordId}`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
