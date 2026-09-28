import type { Stop } from '../types'
import { formatDateTime, formatHours, STOP_INFO } from '../utils'

export function StopList({ stops }: { stops: Stop[] }) {
  return (
    <ol className="stops">
      {stops.map((stop) => (
        <li key={stop.id}>
          <span className="dot" style={{ background: STOP_INFO[stop.type].color }} />
          <div>
            <strong>{STOP_INFO[stop.type].label}</strong>
            {stop.duration_hours > 0 && <span className="muted"> · {formatHours(stop.duration_hours)}</span>}
            <div className="muted">{stop.label}</div>
          </div>
          <div className="stop-time">
            {formatDateTime(stop.arrival)}
            <div className="muted">mi {Math.round(stop.miles_from_start)}</div>
          </div>
        </li>
      ))}
    </ol>
  )
}
