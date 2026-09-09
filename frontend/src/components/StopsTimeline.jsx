import { STOP_META, fmtDateTime, fmtHours } from '../format.js'

export default function StopsTimeline({ stops }) {
  return (
    <ol className="timeline">
      {stops.map((s, i) => {
        const meta = STOP_META[s.kind]
        return (
          <li key={i} className="timeline-item">
            <span className="timeline-dot" style={{ background: meta.color }} />
            <div className="timeline-body">
              <div className="timeline-head">
                <strong>{meta.label}</strong>
                <span className="timeline-mile">mile {Math.round(s.route_miles).toLocaleString()}</span>
              </div>
              <div>{s.label}</div>
              <div className="muted">
                {fmtDateTime(s.start)}
                {s.duration_hours > 0 && ` · ${fmtHours(s.duration_hours)}`}
              </div>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
