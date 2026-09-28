import type { DailyLog, DutyStatus } from '../types'
import { hourToClock } from '../utils'

// Layout of the paper log (SVG units)
const W = 1000
const H = 560
const LEFT = 150 // grid left edge
const RIGHT = 900 // grid right edge
const TOP = 150 // grid top edge
const ROW = 36
const HOUR = (RIGHT - LEFT) / 24

const ROWS: { key: DutyStatus; label: string }[] = [
  { key: 'off_duty', label: '1. Off Duty' },
  { key: 'sleeper_berth', label: '2. Sleeper Berth' },
  { key: 'driving', label: '3. Driving' },
  { key: 'on_duty', label: '4. On Duty' },
]

const x = (hour: number) => LEFT + hour * HOUR
const y = (status: DutyStatus) => TOP + ROWS.findIndex((r) => r.key === status) * ROW + ROW / 2
const round = (n: number) => Math.round(n * 100) / 100
const clip = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s)

export function LogSheet({ log }: { log: DailyLog }) {
  const bottom = TOP + ROW * 4
  const [year, month, day] = log.date.split('-')

  // One continuous pen line: horizontal along each status, vertical at each change.
  const path = log.entries
    .map((e, i) => `${i ? 'L' : 'M'}${x(e.start_hour)},${y(e.status)} L${x(e.end_hour)},${y(e.status)}`)
    .join(' ')

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="log-sheet">
      <rect width={W} height={H} fill="#fffdf8" />

      {/* Header */}
      <text x={24} y={40} className="title">Drivers Daily Log</text>
      <text x={330} y={40} className="pen">{month} / {day} / {year}</text>
      <text x={24} y={75} className="label">From:</text>
      <text x={70} y={75} className="pen">{log.from_location}</text>
      <text x={500} y={75} className="label">To:</text>
      <text x={530} y={75} className="pen">{log.to_location}</text>
      <text x={24} y={105} className="label">Total miles driving today:</text>
      <text x={200} y={105} className="pen">{Math.round(log.total_miles)}</text>
      <text x={976} y={40} className="small" textAnchor="end">Day {log.day_number}</text>

      {/* Hour labels */}
      <rect x={LEFT - 14} y={TOP - 22} width={RIGHT - LEFT + 28} height={22} fill="#1b2533" />
      {Array.from({ length: 25 }, (_, h) => (
        <text key={h} x={x(h)} y={TOP - 7} className="hour" textAnchor="middle">
          {h === 0 || h === 24 ? 'M' : h === 12 ? 'N' : h % 12}
        </text>
      ))}
      <text x={945} y={TOP - 7} className="label" textAnchor="middle">Total</text>

      {/* Grid rows with 15-minute ticks */}
      {ROWS.map((row, i) => {
        const top = TOP + i * ROW
        return (
          <g key={row.key}>
            <rect x={LEFT} y={top} width={RIGHT - LEFT} height={ROW} fill={i % 2 ? '#f5f3ec' : '#fff'} stroke="#1b2533" />
            <text x={24} y={top + ROW / 2 + 4} className="label">{row.label}</text>
            <text x={945} y={top + ROW / 2 + 5} className="pen" textAnchor="middle">{round(log.totals[row.key])}</text>
            {Array.from({ length: 96 }, (_, q) => (
              <line
                key={q}
                x1={x(q / 4)}
                x2={x(q / 4)}
                y1={top}
                y2={top + (q % 4 === 0 ? ROW : q % 2 === 0 ? ROW * 0.5 : ROW * 0.25)}
                stroke="#1b2533"
                strokeWidth={q % 4 === 0 ? 0.8 : 0.5}
              />
            ))}
          </g>
        )
      })}
      <text x={945} y={bottom + 18} className="pen" textAnchor="middle">
        = {round(Object.values(log.totals).reduce((a, b) => a + b, 0))}
      </text>

      <path d={path} fill="none" stroke="#1d4ed8" strokeWidth={3} strokeLinejoin="round" />

      {/* Remarks: a tick at each change of duty status with the location */}
      <text x={24} y={bottom + 30} className="label">Remarks</text>
      {log.remarks.map((r, i) => (
        <g key={i}>
          <line x1={x(r.hour)} x2={x(r.hour)} y1={bottom} y2={bottom + 22} stroke="#1d4ed8" strokeDasharray="2 2" />
          <text
            x={x(r.hour) + 3}
            y={bottom + 30}
            transform={`rotate(45 ${x(r.hour) + 3} ${bottom + 30})`}
            className="remark"
          >
            <title>{`${hourToClock(r.hour)} ${r.location} - ${r.note}`}</title>
            {hourToClock(r.hour)} {clip(r.location, 24)}
          </text>
        </g>
      ))}

      {/* Recap */}
      <line x1={24} x2={976} y1={H - 70} y2={H - 70} stroke="#1b2533" strokeWidth={2} />
      <text x={24} y={H - 40} className="label">Recap (70 hr / 8 day)</text>
      <text x={260} y={H - 40} className="small">On duty today:</text>
      <text x={350} y={H - 40} className="pen">{round(log.recap.on_duty_today)}</text>
      <text x={430} y={H - 40} className="small">A. Cycle hours used:</text>
      <text x={550} y={H - 40} className="pen">{round(log.recap.cycle_used)}</text>
      <text x={630} y={H - 40} className="small">B. Available tomorrow:</text>
      <text x={765} y={H - 40} className="pen">{round(log.recap.cycle_available)}</text>
      <text x={830} y={H - 40} className="small">34-hr restart:</text>
      <text x={915} y={H - 40} className="pen">{log.recap.restart_taken ? 'Yes' : 'No'}</text>
    </svg>
  )
}
