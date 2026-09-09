export const STATUS_LABEL = {
  off_duty: 'Off duty',
  sleeper_berth: 'Sleeper berth',
  driving: 'Driving',
  on_duty: 'On duty (not driving)',
}

export const STOP_META = {
  start: { label: 'Start', color: '#14295C' },
  pickup: { label: 'Pickup', color: '#2E8B57' },
  dropoff: { label: 'Drop-off', color: '#C7412B' },
  fuel: { label: 'Fuel', color: '#E0A030' },
  break: { label: '30 minute break', color: '#5B8DEF' },
  rest: { label: '10 hour rest', color: '#6C5CE7' },
  restart: { label: '34 hour restart', color: '#8E44AD' },
}

export function fmtHours(h) {
  if (h == null) return '—'
  const totalMin = Math.round(h * 60)
  const hh = Math.floor(totalMin / 60)
  const mm = totalMin % 60
  if (hh === 0) return `${mm} min`
  return mm ? `${hh}h ${mm}m` : `${hh}h`
}

export function fmtClock(hourFloat) {
  const totalMin = Math.round(hourFloat * 60)
  const hh = Math.floor(totalMin / 60) % 24
  const mm = totalMin % 60
  const ampm = hh >= 12 ? 'pm' : 'am'
  const h12 = hh % 12 === 0 ? 12 : hh % 12
  return `${h12}:${String(mm).padStart(2, '0')} ${ampm}`
}

export function fmtDateTime(iso) {
  const d = new Date(iso)
  return d.toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

export function fmtDate(isoDate) {
  const [y, m, d] = isoDate.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
}

export function fmtMiles(m) {
  return `${Math.round(m).toLocaleString()} mi`
}

export function localDateTimeValue(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  d = new Date(d)
  d.setMinutes(Math.ceil(d.getMinutes() / 15) * 15, 0, 0)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
