import type { TripInput, TripPlan } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? '/api'

export async function planTrip(input: TripInput): Promise<TripPlan> {
  const res = await fetch(`${API_URL}/trips/plan/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const message = body?.detail ?? Object.values(body ?? {}).flat()[0] ?? `Request failed (${res.status})`
    throw new Error(String(message))
  }
  return body
}
