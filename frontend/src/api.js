const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export async function planTrip(inputs) {
  const res = await fetch(`${API_BASE}/api/trips/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(inputs),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = data.detail || Object.values(data).flat().join(' ') || `Request failed (${res.status})`
    throw new Error(detail)
  }
  return data
}
