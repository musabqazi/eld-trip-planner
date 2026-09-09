import { fmtClock, fmtDate } from '../format.js'

// Geometry of the sheet (SVG user units)
const W = 1040
const GRID_X = 130
const GRID_W = 816 // 24 hours × 34 units
const HOUR_W = GRID_W / 24
const ROW_H = 44
const GRID_Y = 196
const ROWS = ['off_duty', 'sleeper_berth', 'driving', 'on_duty']
const ROW_LABELS = {
  off_duty: ['1. Off Duty'],
  sleeper_berth: ['2. Sleeper', 'Berth'],
  driving: ['3. Driving'],
  on_duty: ['4. On Duty', '(not driving)'],
}
const REMARKS_Y = GRID_Y + ROWS.length * ROW_H
const REMARKS_H = 225
const H = REMARKS_Y + REMARKS_H + 90

const xAt = (hour) => GRID_X + hour * HOUR_W
const rowMid = (status) => GRID_Y + ROWS.indexOf(status) * ROW_H + ROW_H / 2

function hourLabel(h) {
  if (h === 0) return 'Mid-\nnight'
  if (h === 12) return 'Noon'
  return String(h > 12 ? h - 12 : h)
}

function HourScale({ y }) {
  const labels = []
  for (let h = 0; h <= 24; h++) {
    const x = xAt(h)
    const text = hourLabel(h === 24 ? 0 : h)
    labels.push(
      <text key={h} x={x} y={y} textAnchor="middle" className="ls-hour">
        {text.split('\n').map((line, i) => (
          <tspan key={i} x={x} dy={i === 0 ? 0 : 10}>
            {line}
          </tspan>
        ))}
      </text>,
    )
  }
  return <g>{labels}</g>
}

function Grid() {
  const lines = []
  ROWS.forEach((status, r) => {
    const top = GRID_Y + r * ROW_H
    const bottom = top + ROW_H
    // row background band for the driving row, to make the key line easy to read
    for (let h = 0; h < 24; h++) {
      const x0 = xAt(h)
      lines.push(<line key={`${r}-${h}-hr`} x1={x0} y1={top} x2={x0} y2={bottom} className="ls-tick-hour" />)
      // quarter-hour ticks: 15 & 45 short, 30 medium
      ;[0.25, 0.5, 0.75].forEach((q) => {
        const x = x0 + q * HOUR_W
        const len = q === 0.5 ? ROW_H * 0.42 : ROW_H * 0.24
        lines.push(<line key={`${r}-${h}-${q}`} x1={x} y1={top} x2={x} y2={top + len} className="ls-tick" />)
      })
    }
    lines.push(<line key={`${r}-bottom`} x1={GRID_X} y1={bottom} x2={GRID_X + GRID_W} y2={bottom} className="ls-row" />)
  })
  lines.push(<line key="top" x1={GRID_X} y1={GRID_Y} x2={GRID_X + GRID_W} y2={GRID_Y} className="ls-row" />)
  lines.push(<line key="right" x1={GRID_X + GRID_W} y1={GRID_Y} x2={GRID_X + GRID_W} y2={GRID_Y + ROWS.length * ROW_H} className="ls-row" />)
  lines.push(<line key="left" x1={GRID_X} y1={GRID_Y} x2={GRID_X} y2={GRID_Y + ROWS.length * ROW_H} className="ls-row" />)
  return <g>{lines}</g>
}

function DutyLine({ segments }) {
  if (!segments.length) return null
  const d = []
  segments.forEach((seg, i) => {
    const y = rowMid(seg.status)
    const x0 = xAt(seg.start_hour)
    const x1 = xAt(seg.end_hour)
    if (i === 0) d.push(`M ${x0} ${y}`)
    else d.push(`L ${x0} ${y}`) // vertical connector from previous row
    d.push(`L ${x1} ${y}`)
  })
  return <path d={d.join(' ')} className="ls-duty" />
}

function Remarks({ remarks }) {
  // Draw a small tick at the hour of each status change and the remark text angled beneath it,
  // like a hand-filled paper log. Alternate the vertical offset so nearby remarks don't collide.
  const baseY = REMARKS_Y + 34
  return (
    <g>
      {remarks.map((r, i) => {
        const x = xAt(r.hour)
        const offset = (i % 3) * 13
        return (
          <g key={i}>
            <line x1={x} y1={REMARKS_Y + 18} x2={x} y2={REMARKS_Y + 28} className="ls-tick-hour" />
            <text
              x={x}
              y={baseY + offset}
              className="ls-remark"
              transform={`rotate(58 ${x} ${baseY + offset})`}
            >
              {r.text}
            </text>
          </g>
        )
      })}
    </g>
  )
}

function Field({ x, y, w, label, value, align = 'left' }) {
  const tx = align === 'center' ? x + w / 2 : x
  return (
    <g>
      <text x={tx} y={y} textAnchor={align === 'center' ? 'middle' : 'start'} className="ls-value">
        {value}
      </text>
      <line x1={x} y1={y + 6} x2={x + w} y2={y + 6} className="ls-field" />
      <text x={tx} y={y + 19} textAnchor={align === 'center' ? 'middle' : 'start'} className="ls-label">
        {label}
      </text>
    </g>
  )
}

export default function LogSheet({ log, trip, totalDays }) {
  const { inputs, places } = trip
  const totals = log.totals
  const carrier = 'Spotter Freight Lines'
  const [y, m, d] = log.date.split('-')

  return (
    <figure className="logsheet">
      <figcaption className="logsheet-caption">
        <span className="logsheet-day">Day {log.day} of {totalDays}</span>
        <span className="logsheet-date">{fmtDate(log.date)}</span>
        <span className="logsheet-miles">{Math.round(log.miles_driven).toLocaleString()} miles driven</span>
        <span className="logsheet-hint">Swipe sideways to see the full sheet</span>
      </figcaption>
      <div className="logsheet-scroll">
      <svg viewBox={`0 0 ${W} ${H}`} className="ls" role="img" aria-label={`Driver's daily log for ${fmtDate(log.date)}`}>
        {/* Title block */}
        <text x={28} y={36} className="ls-title">Drivers Daily Log</text>
        <text x={28} y={52} className="ls-label">(24 hours)</text>
        <text x={W - 28} y={30} textAnchor="end" className="ls-label">Original - File at home terminal.</text>
        <text x={W - 28} y={44} textAnchor="end" className="ls-label">Duplicate - Driver retains in his/her possession for 8 days.</text>

        <Field x={260} y={40} w={60} label="(month)" value={m} align="center" />
        <text x={328} y={40} className="ls-value">/</text>
        <Field x={340} y={40} w={60} label="(day)" value={d} align="center" />
        <text x={408} y={40} className="ls-value">/</text>
        <Field x={420} y={40} w={80} label="(year)" value={y} align="center" />

        <Field x={28} y={92} w={150} label="Total Miles Driving Today" value={Math.round(log.miles_driven).toLocaleString()} align="center" />
        <Field x={195} y={92} w={150} label="Total Mileage Today" value={Math.round(log.miles_driven).toLocaleString()} align="center" />
        <Field x={380} y={92} w={300} label="Name of Carrier or Carriers" value={carrier} align="center" />
        <Field x={700} y={92} w={312} label="Main Office Address" value={`${places.current.name}`} align="center" />

        <Field x={28} y={128} w={317} label="Truck/Tractor and Trailer Numbers or License Plate(s)/State" value="TRK 4127 · TRL 88215" align="center" />
        <Field x={380} y={128} w={300} label="From" value={places.current.name} align="center" />
        <Field x={700} y={128} w={312} label="To" value={places.dropoff.name} align="center" />

        {/* Hour scale + grid */}
        <HourScale y={GRID_Y - 12} />
        <Grid />
        {ROWS.map((status) => (
          <text key={status} x={GRID_X - 8} y={rowMid(status) + 1} textAnchor="end" className="ls-rowlabel">
            {ROW_LABELS[status].map((line, i) => (
              <tspan key={i} x={GRID_X - 8} dy={i === 0 ? (ROW_LABELS[status].length > 1 ? -5 : 4) : 12}>
                {line}
              </tspan>
            ))}
          </text>
        ))}
        <DutyLine segments={log.segments} />

        {/* Totals column */}
        <text x={GRID_X + GRID_W + 46} y={GRID_Y - 18} textAnchor="middle" className="ls-label">Total</text>
        <text x={GRID_X + GRID_W + 46} y={GRID_Y - 6} textAnchor="middle" className="ls-label">Hours</text>
        {ROWS.map((status) => (
          <text key={status} x={GRID_X + GRID_W + 46} y={rowMid(status) + 6} textAnchor="middle" className="ls-total">
            {totals[status].toFixed(2).replace(/\.?0+$/, '')}
          </text>
        ))}
        <line x1={GRID_X + GRID_W + 18} y1={REMARKS_Y + 4} x2={GRID_X + GRID_W + 74} y2={REMARKS_Y + 4} className="ls-row" />
        <text x={GRID_X + GRID_W + 46} y={REMARKS_Y + 22} textAnchor="middle" className="ls-total">= {log.total_hours.toFixed(0)}</text>

        {/* Remarks */}
        <text x={28} y={REMARKS_Y + 22} className="ls-section">Remarks</text>
        <HourScale y={REMARKS_Y + 14} />
        <Remarks remarks={log.remarks} />
        <line x1={GRID_X} y1={REMARKS_Y} x2={GRID_X + GRID_W} y2={REMARKS_Y} className="ls-row" />

        {/* Shipping docs */}
        <text x={28} y={REMARKS_Y + REMARKS_H + 20} className="ls-section">Shipping Documents:</text>
        <Field x={28} y={REMARKS_Y + REMARKS_H + 52} w={250} label="DVL or Manifest No." value={`BOL-${y}${m}${d}-${String(log.day).padStart(2, '0')}`} />
        <Field x={310} y={REMARKS_Y + REMARKS_H + 52} w={400} label="Shipper & Commodity" value={`${places.pickup.name}, general freight`} />
        <text x={740} y={REMARKS_Y + REMARKS_H + 34} className="ls-label">Enter name of place you reported and where released</text>
        <text x={740} y={REMARKS_Y + REMARKS_H + 46} className="ls-label">from work and when and where each change of duty</text>
        <text x={740} y={REMARKS_Y + REMARKS_H + 58} className="ls-label">occurred. Use time standard of home terminal.</text>
      </svg>
      </div>

      <ol className="logsheet-events">
        {log.remarks.map((r, i) => (
          <li key={i}>
            <span className="logsheet-time">{fmtClock(r.hour)}</span>
            <span>{r.text}</span>
          </li>
        ))}
      </ol>
    </figure>
  )
}
