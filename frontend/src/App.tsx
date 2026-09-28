import { useState } from 'react'

import { planTrip } from './api'
import { LogSheet } from './components/LogSheet'
import { RouteMap } from './components/RouteMap'
import { StopList } from './components/StopList'
import { TripForm } from './components/TripForm'
import type { TripInput, TripPlan } from './types'
import { formatDateTime, formatHours } from './utils'

export default function App() {
  const [plan, setPlan] = useState<TripPlan | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(input: TripInput) {
    setLoading(true)
    setError('')
    try {
      setPlan(await planTrip(input))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <header className="header">
        <strong>Truck Log Book</strong>
        <span>HOS trip planner &amp; ELD logs</span>
      </header>

      <main className="layout">
        <TripForm loading={loading} onSubmit={handleSubmit} />

        <section className="results">
          {error && <div className="error">{error}</div>}

          {!plan && !error && (
            <div className="card empty">
              {loading ? 'Planning your route…' : 'Enter trip details to see the route, stops and daily logs.'}
            </div>
          )}

          {plan && (
            <>
              <div className="stats">
                <Stat label="Distance" value={`${Math.round(plan.summary.total_miles).toLocaleString()} mi`} />
                <Stat label="Driving" value={formatHours(plan.summary.driving_hours)} />
                <Stat label="Trip time" value={formatHours(plan.summary.total_trip_hours)} />
                <Stat label="Log sheets" value={String(plan.summary.days)} />
                <Stat label="Arrives" value={formatDateTime(plan.summary.trip_end)} />
              </div>

              <div className="card map-card">
                {/* Leaflet only reads bounds on mount, so remount for each new trip */}
                <RouteMap key={`${plan.summary.total_miles}-${plan.summary.trip_end}`} plan={plan} />
                <StopList stops={plan.stops} />
              </div>

              <div className="logs-head">
                <h2>Daily Logs</h2>
                <button onClick={() => window.print()}>Print</button>
              </div>
              {plan.daily_logs.map((log) => (
                <div key={log.date} className="card log-card">
                  <LogSheet log={log} />
                </div>
              ))}
            </>
          )}
        </section>
      </main>
    </>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="card stat">
      <span className="muted">{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
