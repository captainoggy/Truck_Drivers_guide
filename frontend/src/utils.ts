import type { StopType } from './types'

export const STOP_INFO: Record<StopType, { label: string; color: string }> = {
  start: { label: 'Start', color: '#16a34a' },
  pickup: { label: 'Pickup', color: '#2563eb' },
  dropoff: { label: 'Drop-off', color: '#e11d48' },
  fuel: { label: 'Fuel', color: '#ea580c' },
  break: { label: '30-min break', color: '#0891b2' },
  rest: { label: '10-hr rest', color: '#7c3aed' },
  restart: { label: '34-hr restart', color: '#a21caf' },
}

// API datetimes are naive home-terminal times, so parse them as local time.
export const formatDateTime = (iso: string) =>
  new Date(iso).toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' })

export function formatHours(hours: number): string {
  const mins = Math.round(hours * 60)
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return m ? `${h}h ${m}m` : `${h}h`
}

/** 13.5 -> "1:30 PM" */
export function hourToClock(hour: number): string {
  const mins = Math.round(hour * 60)
  const h = Math.floor(mins / 60) % 24
  const m = String(mins % 60).padStart(2, '0')
  return `${h % 12 || 12}:${m} ${h < 12 ? 'AM' : 'PM'}`
}
