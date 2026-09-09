import { useEffect } from 'react'
import { MapContainer, TileLayer, Polyline, CircleMarker, Marker, Popup, Tooltip, useMap } from 'react-leaflet'
import L from 'leaflet'
import { STOP_META, fmtDateTime, fmtHours } from '../format.js'

function FitBounds({ geometry }) {
  const map = useMap()
  useEffect(() => {
    if (geometry?.length) map.fitBounds(L.latLngBounds(geometry), { padding: [32, 32] })
  }, [geometry, map])
  return null
}

function pinIcon(color, letter) {
  return L.divIcon({
    className: 'pin',
    html: `<div class="pin-body" style="background:${color}"><span>${letter}</span></div>`,
    iconSize: [30, 38],
    iconAnchor: [15, 36],
    popupAnchor: [0, -32],
  })
}

const PIN_LETTER = { start: 'S', pickup: 'P', dropoff: 'D' }

export default function RouteMap({ trip }) {
  const { route, stops } = trip
  const center = route.geometry[Math.floor(route.geometry.length / 2)]

  return (
    <MapContainer center={center} zoom={5} className="map" scrollWheelZoom={false}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Polyline positions={route.geometry} pathOptions={{ color: '#14295C', weight: 5, opacity: 0.9 }} />
      <Polyline positions={route.geometry} pathOptions={{ color: '#5B8DEF', weight: 2, opacity: 0.9 }} />
      <FitBounds geometry={route.geometry} />

      {stops.map((s, i) => {
        const meta = STOP_META[s.kind]
        const body = (
          <div className="popup">
            <strong>{meta.label}</strong>
            <div>{s.label}</div>
            <div className="muted">{fmtDateTime(s.start)}{s.duration_hours > 0 ? ` · ${fmtHours(s.duration_hours)}` : ''}</div>
            <div className="muted">Mile {Math.round(s.route_miles).toLocaleString()}</div>
          </div>
        )
        if (PIN_LETTER[s.kind]) {
          return (
            <Marker key={i} position={[s.lat, s.lon]} icon={pinIcon(meta.color, PIN_LETTER[s.kind])}>
              <Popup>{body}</Popup>
            </Marker>
          )
        }
        return (
          <CircleMarker key={i} center={[s.lat, s.lon]} radius={7} pathOptions={{ color: '#fff', weight: 2, fillColor: meta.color, fillOpacity: 1 }}>
            <Tooltip direction="top" offset={[0, -6]}>{meta.label}</Tooltip>
            <Popup>{body}</Popup>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}
