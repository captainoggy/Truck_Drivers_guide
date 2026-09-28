"""LogBuilder: slices a continuous segment timeline into 24-hour daily logs.

Each day starts and ends at midnight (home-terminal time). Time before the
trip starts and after it ends is logged as off duty, so every sheet sums to 24.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from .models import DailyLog, DutyStatus, LogEntry, Remark, Segment, Stop, StopType
from .rules import PROPERTY_CARRYING_70_8, HOSRules


def _hours(delta: timedelta) -> float:
    return delta.total_seconds() / 3600


class LogBuilder:
    def __init__(self, rules: HOSRules = PROPERTY_CARRYING_70_8):
        self.rules = rules

    def build(self, segments: list[Segment], stops: list[Stop], start_cycle: float) -> list[DailyLog]:
        if not segments:
            return []
        first_day = segments[0].start.date()
        last_end = segments[-1].end
        last_day = (last_end - timedelta(microseconds=1)).date()

        logs: list[DailyLog] = []
        cycle = start_cycle
        day = first_day
        while day <= last_day:
            log, cycle = self._build_day(day, len(logs) + 1, segments, stops, cycle)
            logs.append(log)
            day += timedelta(days=1)
        return logs

    def _build_day(self, day, number, segments, stops, cycle_at_start):
        day_start = datetime.combine(day, time.min)
        day_end = day_start + timedelta(days=1)
        log = DailyLog(date=day, day_number=number)

        cursor = day_start
        cycle = cycle_at_start
        for seg in segments:
            if seg.end <= day_start or seg.start >= day_end:
                continue
            start, end = max(seg.start, day_start), min(seg.end, day_end)
            if start > cursor:
                self._add_entry(log, DutyStatus.OFF_DUTY, cursor, start, day_start)
            self._add_entry(log, seg.status, start, end, day_start)
            cursor = end

            if seg.status is DutyStatus.DRIVING and seg.hours > 0:
                log.total_miles += seg.miles * _hours(end - start) / seg.hours
            carried_over = seg.start < day_start
            if not carried_over or seg.status is not DutyStatus.DRIVING:
                # Status carried over midnight is noted so each sheet stands alone.
                log.remarks.append(Remark(
                    hour=_hours(start - day_start), status=seg.status,
                    location=seg.stop.label if seg.stop else "",
                    note=f"(cont.) {seg.note}" if carried_over else seg.note,
                ))
            if seg.end <= day_end:
                cycle = seg.cycle_after
            else:
                on_duty_part = _hours(end - start) if seg.status.is_on_duty else 0.0
                cycle = seg.cycle_before + on_duty_part
            if seg.stop and seg.stop.type is StopType.RESTART and seg.end <= day_end:
                log.restart_taken = True

        if cursor < day_end:
            self._add_entry(log, DutyStatus.OFF_DUTY, cursor, day_end, day_start)

        totals = {s.value: 0.0 for s in DutyStatus}
        for e in log.entries:
            totals[e.status.value] += e.end_hour - e.start_hour
        log.totals = {k: round(v, 2) for k, v in totals.items()}
        log.total_miles = round(log.total_miles, 1)
        log.on_duty_today = round(totals[DutyStatus.DRIVING.value] + totals[DutyStatus.ON_DUTY.value], 2)
        log.cycle_used = round(cycle, 2)
        log.cycle_available = round(max(0.0, self.rules.cycle_limit_hours - cycle), 2)
        log.from_location = self._location_at(stops, day_start)
        log.to_location = self._location_at(stops, day_end)
        return log, cycle

    @staticmethod
    def _add_entry(log: DailyLog, status: DutyStatus, start, end, day_start) -> None:
        s, e = _hours(start - day_start), _hours(end - day_start)
        if e - s <= 1e-9:
            return
        if log.entries and log.entries[-1].status is status and abs(log.entries[-1].end_hour - s) < 1e-9:
            log.entries[-1].end_hour = e  # merge contiguous same-status blocks
        else:
            log.entries.append(LogEntry(status, s, e))

    @staticmethod
    def _location_at(stops: list[Stop], moment: datetime) -> str:
        """Label of the last stop reached at or before `moment`."""
        label = stops[0].label if stops else ""
        for stop in stops:
            if stop.arrival <= moment:
                label = stop.label or label
        return label
