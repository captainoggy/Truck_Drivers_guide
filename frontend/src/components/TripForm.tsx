import { useState } from 'react'

import { TEST_CASES, type TripFormValues } from '../testCases'
import type { TripInput } from '../types'

function today8am(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T08:00`
}

const LOCATION_FIELDS = [
  { key: 'current', label: 'Current location', placeholder: 'e.g. Chicago, IL' },
  { key: 'pickup', label: 'Pickup location', placeholder: 'e.g. St. Louis, MO' },
  { key: 'dropoff', label: 'Drop-off location', placeholder: 'e.g. Phoenix, AZ' },
] as const

interface Props {
  loading: boolean
  onSubmit: (input: TripInput) => void
}

export function TripForm({ loading, onSubmit }: Props) {
  const [form, setForm] = useState<TripFormValues>({
    current: '',
    pickup: '',
    dropoff: '',
    cycle: '0',
    start: today8am(),
  })

  const update = (key: keyof TripFormValues) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      current_location: form.current,
      pickup_location: form.pickup,
      dropoff_location: form.dropoff,
      current_cycle_used: Number(form.cycle),
      start_time: `${form.start}:00`,
    })
  }

  return (
    <aside className="sidebar">
      <form className="card form" onSubmit={submit}>
        <h2>Plan a trip</h2>

        {LOCATION_FIELDS.map((field) => (
          <label key={field.key}>
            <span>{field.label}</span>
            <input required value={form[field.key]} onChange={update(field.key)} placeholder={field.placeholder} />
          </label>
        ))}

        <div className="row">
          <label>
            <span>Cycle used (hrs)</span>
            <input required type="number" min={0} max={70} step={0.25} value={form.cycle} onChange={update('cycle')} />
          </label>
          <label>
            <span>Departure</span>
            <input required type="datetime-local" value={form.start} onChange={update('start')} />
          </label>
        </div>

        <button type="submit" className="primary" disabled={loading}>
          {loading ? 'Planning…' : 'Generate route & logs'}
        </button>
        <p className="hint">
          Property-carrying driver, 70 hr / 8 day cycle. Fuel every 1,000 mi, 1 hr for pickup and drop-off.
        </p>
      </form>

      <div className="card test-cases">
        <h3>Test cases</h3>
        {TEST_CASES.map((tc) => (
          <button key={tc.name} type="button" className="test-case" onClick={() => setForm({ ...form, ...tc.values })}>
            <strong>{tc.name}</strong>
            <span>
              {tc.values.current} → {tc.values.pickup} → {tc.values.dropoff} · {tc.values.cycle} hrs used
            </span>
            <span className="muted">{tc.description}</span>
          </button>
        ))}
      </div>
    </aside>
  )
}
