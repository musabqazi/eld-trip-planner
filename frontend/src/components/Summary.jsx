import { fmtHours, fmtMiles, fmtDateTime } from '../format.js'

export default function Summary({ trip }) {
  const s = trip.summary
  const items = [
    { label: 'Total distance', value: fmtMiles(s.total_miles) },
    { label: 'Driving time', value: fmtHours(s.total_driving_hours) },
    { label: 'Trip duration', value: fmtHours(s.total_trip_hours) },
    { label: 'Log sheets', value: s.days },
    { label: 'Fuel stops', value: s.fuel_stops },
    { label: '10 hour rests', value: s.rest_periods },
    { label: '30 minute breaks', value: s.breaks },
    { label: 'Cycle at arrival', value: `${s.cycle_hours_at_end} / 70 h` },
  ]
  return (
    <section className="summary">
      <div className="summary-route">
        <span>{trip.places.current.name}</span>
        <span className="arrow">→</span>
        <span>{trip.places.pickup.name}</span>
        <span className="arrow">→</span>
        <span>{trip.places.dropoff.name}</span>
      </div>
      <p className="muted">
        Leaves {fmtDateTime(s.trip_start)}, delivers {fmtDateTime(s.trip_end)}
        {s.restarts > 0 && `, including a 34 hour restart`}
      </p>
      <dl className="stats">
        {items.map((it) => (
          <div key={it.label}>
            <dt>{it.label}</dt>
            <dd>{it.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
