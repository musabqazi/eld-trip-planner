# ELD Trip Planner

A full-stack app (Django + React) that takes a trip's details and returns a driving route with every
fuel stop, break and rest marked on a map, plus filled-in FMCSA Driver's Daily Log sheets for each day
of the trip.

**Inputs:** current location · pickup location · drop-off location · current cycle used (hrs) · departure time
**Outputs:** interactive route map with stops · trip summary · one drawn ELD log sheet per day

Built for the Spotter AI Full Stack Developer assessment.

---

## How it works

```
React (Vite)  ──POST /api/trips/──▶  Django REST API
                                       ├─ geocoding.py    Nominatim (OpenStreetMap) — free, no key
                                       ├─ routing.py      OSRM public server      — free, no key
                                       ├─ hos_planner.py  Hours-of-Service simulation
                                       ├─ daily_logs.py   Slice duty segments into 24-hr log sheets
                                       └─ Trip model      Saves inputs + result (SQLite)
```

### Hours-of-Service rules applied (49 CFR §395, property-carrying)

| Rule | Implementation |
|---|---|
| 11-hour driving limit | Driving stops when 11 h reached in a window |
| 14-hour driving window | Window starts at first on-duty work; no driving after 14 h |
| 30-minute break | Required after 8 cumulative driving hours; a 30 min+ on-duty stop (fuel, pickup) also satisfies it |
| 10-hour rest | Taken in the sleeper berth; resets the 11/14-hour clocks |
| 70-hour / 8-day cycle | Starts from "current cycle used"; driving is capped at the remaining hours |
| 34-hour restart | Inserted automatically when the 70-hour cycle is exhausted |
| Fuel | 30 min on-duty stop at least every 1,000 miles |
| Pickup / drop-off | 1 hour on duty (not driving) each |
| Adverse conditions | Not applied (assessment assumption) |

The planner (`backend/trips/services/hos_planner.py`) walks the route and always drives the largest
legal block before the next required stop, producing a list of duty-status segments. `daily_logs.py`
then cuts those segments at midnight so each sheet totals exactly 24 hours, with remarks for every
change of duty status. The frontend draws each sheet as SVG on the standard 4-line grid.

---

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver                              # http://localhost:8000
```

Run the tests (offline — they use a straight-line route, no network needed):

```bash
python manage.py test
```

### Frontend

```bash
cd frontend
npm install
npm run dev                                             # http://localhost:5173
```

The Vite dev server proxies `/api` to `http://localhost:8000`, so no env var is needed locally.

---

## API

`POST /api/trips/`

```json
{
  "current_location": "Chicago, IL",
  "pickup_location": "Denver, CO",
  "dropoff_location": "Los Angeles, CA",
  "current_cycle_used": 20,
  "start_time": "2026-09-08T06:00:00"
}
```

Returns `201` with the saved trip. `result` contains:

- `places` — geocoded current / pickup / dropoff
- `route` — `geometry` (lat/lon polyline), `distance_miles`, `duration_hours`, `legs`
- `stops` — ordered list of `start | pickup | dropoff | fuel | break | rest | restart` with coordinates, times and mileage
- `summary` — totals (miles, driving hours, trip hours, number of log sheets, fuel stops, rests, breaks)
- `daily_logs` — one entry per calendar day: `segments` (status, start/end hour), `totals` per status, `miles_driven`, `remarks`

`GET /api/trips/` lists recent trips; `GET /api/trips/<id>/` fetches one.

Errors from geocoding/routing (unknown place, no drivable route) return `400` with a `detail` message.

---

## Deploying

### Backend → Vercel

```bash
cd backend
vercel            # follow prompts; vercel.json is already configured
```

Set env vars in the Vercel project: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `VERCEL=1` (migrations run automatically on cold start). SQLite lives in `/tmp` on
Vercel (ephemeral) which is fine — the app is stateless apart from the convenience trip history.
Alternatively deploy to Render with the included `backend/render.yaml` blueprint (keeps `VERCEL` unset).

### Frontend → Vercel

```bash
cd frontend
vercel
```

Set `VITE_API_URL=https://<your-backend>.vercel.app` in the project's environment variables, then redeploy.

---

## Project layout

```
backend/
  config/            settings, urls, wsgi (Vercel entry: config/wsgi.py)
  trips/
    models.py        Trip
    views.py         TripListCreateView, TripDetailView
    serializers.py
    services/
      geocoding.py   Nominatim
      routing.py     OSRM + route-mile interpolation for stop coordinates
      hos_planner.py HOS simulation
      daily_logs.py  Log sheet slicing
      trip_planner.py Orchestrator
    tests.py         10 offline tests: every HOS rule + the API contract
frontend/
  src/
    App.jsx
    api.js
    format.js
    components/
      TripForm.jsx        inputs + example trips
      RouteMap.jsx        Leaflet map, OSM tiles, stop markers
      StopsTimeline.jsx
      Summary.jsx
      LogSheet.jsx        SVG Driver's Daily Log
    styles.css
```

## Notes on free services

- **Nominatim** asks for a descriptive `User-Agent` and ≤1 request/second. Fine for an assessment; for
  production, self-host or use a keyed geocoder.
- **OSRM demo server** (`router.project-osrm.org`) is rate-limited and has no SLA. Point `OSRM_URL` at
  your own instance if needed.
- **OpenStreetMap tiles** are free under the OSM tile usage policy.
