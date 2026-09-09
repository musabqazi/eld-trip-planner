import { useState } from 'react'
import { localDateTimeValue } from '../format.js'

const EXAMPLES = [
  { label: 'Chicago → Denver → Los Angeles', current_location: 'Chicago, IL', pickup_location: 'Denver, CO', dropoff_location: 'Los Angeles, CA', current_cycle_used: 20 },
  { label: 'Dallas → Atlanta → New York', current_location: 'Dallas, TX', pickup_location: 'Atlanta, GA', dropoff_location: 'New York, NY', current_cycle_used: 55 },
  { label: 'Seattle → Portland → Sacramento', current_location: 'Seattle, WA', pickup_location: 'Portland, OR', dropoff_location: 'Sacramento, CA', current_cycle_used: 8 },
]

export default function TripForm({ onSubmit, loading }) {
  const [form, setForm] = useState({
    current_location: '',
    pickup_location: '',
    dropoff_location: '',
    current_cycle_used: 0,
    start_time: localDateTimeValue(),
  })

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = (e) => {
    e.preventDefault()
    onSubmit({
      ...form,
      current_cycle_used: Number(form.current_cycle_used) || 0,
      // Send the wall-clock time as entered: log sheets use home-terminal time, not UTC.
      start_time: form.start_time ? `${form.start_time}:00` : null,
    })
  }

  const loadExample = (ex) => setForm((f) => ({ ...f, ...ex, label: undefined }))

  return (
    <form className="trip-form" onSubmit={submit}>
      <h2>Trip details</h2>

      <label>
        <span>Current location</span>
        <input required value={form.current_location} onChange={set('current_location')} placeholder="City, State" autoComplete="off" />
      </label>
      <label>
        <span>Pickup location</span>
        <input required value={form.pickup_location} onChange={set('pickup_location')} placeholder="City, State" autoComplete="off" />
      </label>
      <label>
        <span>Drop-off location</span>
        <input required value={form.dropoff_location} onChange={set('dropoff_location')} placeholder="City, State" autoComplete="off" />
      </label>

      <div className="form-row">
        <label>
          <span>Cycle used (hrs)</span>
          <input type="number" min="0" max="70" step="0.5" required value={form.current_cycle_used} onChange={set('current_cycle_used')} />
          <small>Hours already worked in the last 8 days, out of 70</small>
        </label>
        <label>
          <span>Departure</span>
          <input type="datetime-local" value={form.start_time} onChange={set('start_time')} />
          <small>Local time at your home terminal</small>
        </label>
      </div>

      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? 'Planning your trip...' : 'Plan trip'}
      </button>

      <div className="examples">
        <span>Or try one of these</span>
        {EXAMPLES.map((ex) => (
          <button type="button" key={ex.label} onClick={() => loadExample(ex)} className="btn-link">
            {ex.label}
          </button>
        ))}
      </div>
    </form>
  )
}
