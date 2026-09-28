# Truck Log Book - HOS Trip Planner & ELD Logs

Enter a current location, pickup, drop-off and hours already used in the 70-hr cycle.
The app routes the trip, schedules every stop the FMCSA Hours-of-Service rules require,
shows them on a map, and draws a filled-out **Driver's Daily Log** for each day of the trip.

**Stack:** Django + DRF · React + TypeScript (Vite) · Leaflet/OpenStreetMap · OSRM routing · Photon geocoding · Docker

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8080. nginx serves the React app and proxies `/api` to Django.

## Repo layout

```
.
├── .env.example          # all config lives here (copied to .env)
├── docker-compose.yml
├── backend/              # Django API
│   ├── hos/              # pure-Python HOS engine (no Django)
│   ├── routing/          # map API adapters (OSRM, Photon, offline city lookup)
│   ├── services/         # PlanTripService - the one use case
│   ├── trips/            # HTTP: views + serializers
│   └── tests/
└── frontend/             # React app (served by nginx in Docker)
    └── src/components/   # TripForm, RouteMap, StopList, LogSheet
```

## Rules modelled (property-carrying driver, 70 hr / 8 day)

| Rule | Behaviour |
|---|---|
| 11-hour driving limit | 10-hr rest (sleeper berth) once 11 hrs are driven |
| 14-hour window | no driving after the 14th hour since coming on duty |
| 30-minute break | after 8 cumulative hrs driving (any 30 min not driving counts) |
| 70-hr / 8-day cycle | 34-hr restart when the cycle runs out |
| Fuel | 30-min on-duty stop at least every 1,000 miles |
| Pickup / drop-off | 1 hr on duty each |

Assumptions: no adverse conditions, times are home-terminal time, and "cycle used" is treated
as the current rolling total (earlier days don't roll off during the trip - a conservative simplification).

## How the backend is designed

- **Service layer** - `PlanTripService` runs geocode → route → HOS simulation → daily logs; views stay thin.
- **Adapters** - `Geocoder`, `ReverseGeocoder` and `RoutingProvider` interfaces; swap providers in `routing/factory.py`.
- **DriverClock** - owns the 11/14/8/70-hour counters; the `TripPlanner` asks it how long it may drive next.
- **LogBuilder** - cuts the continuous timeline at midnight into 24-hour sheets with totals, remarks and recap.
- Remark locations ("12 mi NE of Amarillo, TX") come from an offline GeoNames town list (CC BY 4.0), so they're instant.

## Local development (without Docker)

```bash
cp .env.example .env

cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py runserver      # http://localhost:8000
.venv/bin/pytest                          # HOS engine + API tests

cd frontend
npm install && npm run dev                # http://localhost:5173 (proxies /api to :8000)
```

## API

`POST /api/trips/plan/`

```json
{
  "current_location": "Chicago, IL",
  "pickup_location": "St. Louis, MO",
  "dropoff_location": "Phoenix, AZ",
  "current_cycle_used": 18,
  "start_time": "2026-09-28T08:00:00"
}
```

Returns `route`, `stops`, `segments`, `daily_logs` (entries, totals, remarks, recap) and `summary`.
