import { useState } from 'react'
import { planTrip } from './api.js'
import TripForm from './components/TripForm.jsx'
import RouteMap from './components/RouteMap.jsx'
import StopsTimeline from './components/StopsTimeline.jsx'
import Summary from './components/Summary.jsx'
import LogSheet from './components/LogSheet.jsx'

export default function App() {
  const [trip, setTrip] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (inputs) => {
    setLoading(true)
    setError('')
    try {
      const data = await planTrip(inputs)
      setTrip(data.result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead-inner">
          <div className="brand">
            <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden="true">
              <circle cx="16" cy="16" r="14" fill="none" stroke="currentColor" strokeWidth="2.5" strokeDasharray="6 4" />
              <path d="M16 8v8l5 3" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
            <span>ELD Trip Planner</span>
          </div>
          <p className="tagline">Plan a trip, see every stop on the map, and print the daily logs</p>
        </div>
      </header>

      <main className="layout">
        <aside className="sidebar">
          <TripForm onSubmit={handleSubmit} loading={loading} />
          {error && (
            <div className="error" role="alert">
              <strong>Could not plan this trip.</strong> {error}
            </div>
          )}
          <details className="rules">
            <summary>Rules applied</summary>
            <ul>
              <li>Property carrying driver, 70 hours in 8 days</li>
              <li>Up to 11 hours driving inside a 14 hour window</li>
              <li>30 minute break after 8 hours of driving</li>
              <li>10 hour rest in the sleeper berth resets the day</li>
              <li>34 hour restart once the 70 hours are used up</li>
              <li>Fuel stop of 30 minutes at least every 1,000 miles</li>
              <li>1 hour each for pickup and drop-off</li>
            </ul>
          </details>
        </aside>

        <section className="results">
          {!trip && !loading && (
            <div className="empty">
              <h2>Plan a trip to get started</h2>
              <p>Enter where you are, where you pick up and where you deliver. You get the route with every fuel stop, break and rest marked on the map, and a filled-in log sheet for each day.</p>
            </div>
          )}
          {loading && (
            <div className="empty">
              <div className="spinner" aria-hidden="true" />
              <p>Finding the route and working out the hours. This can take a few seconds.</p>
            </div>
          )}
          {trip && !loading && (
            <>
              <Summary trip={trip} />

              <div className="map-card">
                <RouteMap trip={trip} />
              </div>

              <div className="two-col">
                <section>
                  <h2>Stops and rests</h2>
                  <StopsTimeline stops={trip.stops} />
                </section>
                <section>
                  <h2>Route legs</h2>
                  <table className="legs">
                    <tbody>
                      {trip.route.legs.map((l) => (
                        <tr key={l.name}>
                          <td>{l.name}</td>
                          <td>{Math.round(l.distance_miles).toLocaleString()} mi</td>
                          <td>{l.duration_hours.toFixed(1)} h drive</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <h2 className="mt">Assumptions</h2>
                  <ul className="assumptions">
                    {trip.assumptions.map((a) => <li key={a}>{a}</li>)}
                  </ul>
                </section>
              </div>

              <section className="logs">
                <div className="logs-head">
                  <h2>Daily log sheets</h2>
                  <button type="button" className="btn-secondary" onClick={() => window.print()}>Print logs</button>
                </div>
                {trip.daily_logs.map((log) => (
                  <LogSheet key={log.date} log={log} trip={trip} totalDays={trip.daily_logs.length} />
                ))}
              </section>
            </>
          )}
        </section>
      </main>
    </div>
  )
}
