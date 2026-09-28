// Mirrors the Django API response (backend/trips/serializers.py).

export type DutyStatus = 'off_duty' | 'sleeper_berth' | 'driving' | 'on_duty'
export type StopType = 'start' | 'pickup' | 'dropoff' | 'fuel' | 'break' | 'rest' | 'restart'

export interface TripInput {
  current_location: string
  pickup_location: string
  dropoff_location: string
  current_cycle_used: number
  start_time: string
}

export interface Stop {
  id: number
  type: StopType
  label: string
  lat: number
  lng: number
  arrival: string
  duration_hours: number
  miles_from_start: number
}

export interface DailyLog {
  date: string
  day_number: number
  from_location: string
  to_location: string
  total_miles: number
  totals: Record<DutyStatus, number>
  entries: { status: DutyStatus; start_hour: number; end_hour: number }[]
  remarks: { hour: number; status: DutyStatus; location: string; note: string }[]
  recap: { on_duty_today: number; cycle_used: number; cycle_available: number; restart_taken: boolean }
}

export interface TripPlan {
  route: { distance_miles: number; geometry: [number, number][] }
  stops: Stop[]
  daily_logs: DailyLog[]
  summary: {
    total_miles: number
    driving_hours: number
    total_trip_hours: number
    days: number
    trip_end: string
  }
}
