import 'leaflet/dist/leaflet.css'

import L from 'leaflet'
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from 'react-leaflet'

import type { TripPlan } from '../types'
import { formatDateTime, formatHours, STOP_INFO } from '../utils'

export function RouteMap({ plan }: { plan: TripPlan }) {
  const bounds = L.latLngBounds(plan.route.geometry)

  return (
    <MapContainer className="map" bounds={bounds} boundsOptions={{ padding: [30, 30] }} scrollWheelZoom={false}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Polyline positions={plan.route.geometry} pathOptions={{ color: '#2563eb', weight: 4 }} />
      {plan.stops.map((stop) => {
        const major = ['start', 'pickup', 'dropoff'].includes(stop.type)
        return (
          <CircleMarker
            key={stop.id}
            center={[stop.lat, stop.lng]}
            radius={major ? 10 : 7}
            pathOptions={{ color: '#fff', weight: 2, fillColor: STOP_INFO[stop.type].color, fillOpacity: 1 }}
          >
            <Popup>
              <strong>{STOP_INFO[stop.type].label}</strong>
              <br />
              {stop.label}
              <br />
              {formatDateTime(stop.arrival)}
              {stop.duration_hours > 0 && ` · ${formatHours(stop.duration_hours)}`}
            </Popup>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}
