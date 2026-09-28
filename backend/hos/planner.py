"""TripPlanner: simulates a trip minute-by-minute against the HOS rules.

Output is a continuous timeline of duty-status segments plus the stops
(pickup, fuel, breaks, rests, restarts) that must appear on the map.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .clock import DriverClock
from .models import DutyStatus, Segment, Stop, StopType
from .rules import PROPERTY_CARRYING_70_8, HOSRules
from .track import RouteTrack

EPS = 1e-6
FALLBACK_SPEED_MPH = 55.0


@dataclass
class Leg:
    distance_miles: float
    duration_hours: float

    @property
    def speed_mph(self) -> float:
        if self.duration_hours <= 0:
            return FALLBACK_SPEED_MPH
        return self.distance_miles / self.duration_hours


class TripPlanner:
    def __init__(self, rules: HOSRules = PROPERTY_CARRYING_70_8):
        self.rules = rules

    def plan(
        self,
        to_pickup: Leg,
        to_dropoff: Leg,
        track: RouteTrack,
        start_time: datetime,
        cycle_used: float,
    ) -> tuple[list[Segment], list[Stop]]:
        self.track = track
        self.clock = DriverClock(self.rules, cycle_used=min(cycle_used, self.rules.cycle_limit_hours))
        self.now = start_time
        self.miles = 0.0
        self.miles_since_fuel = 0.0
        self.segments: list[Segment] = []
        self.stops: list[Stop] = []
        self.last_stop = self._add_stop(StopType.START, 0.0)

        self._drive(to_pickup)
        self._stop(StopType.PICKUP, DutyStatus.ON_DUTY, self.rules.pickup_hours, "Pickup - loading")
        self._drive(to_dropoff)
        self._stop(StopType.DROPOFF, DutyStatus.ON_DUTY, self.rules.dropoff_hours, "Drop-off - unloading")
        return self.segments, self.stops

    # -- driving -------------------------------------------------------------
    def _drive(self, leg: Leg) -> None:
        remaining = leg.distance_miles
        speed = leg.speed_mph
        while remaining > EPS:
            if self.miles_since_fuel >= self.rules.fuel_interval_miles - EPS:
                self._stop(StopType.FUEL, DutyStatus.ON_DUTY, self.rules.fuel_stop_hours, "Fueling")
                continue

            available = self.clock.max_drive_hours()
            if available <= EPS:
                self._take_required_rest()
                continue

            to_fuel = self.rules.fuel_interval_miles - self.miles_since_fuel
            miles = min(available * speed, remaining, to_fuel)
            self._segment(DutyStatus.DRIVING, miles / speed, "Driving", miles=miles, at=self.last_stop)
            remaining -= miles

    def _take_required_rest(self) -> None:
        c = self.clock
        if c.cycle_left() <= EPS:
            self._stop(StopType.RESTART, DutyStatus.OFF_DUTY, self.rules.restart_hours,
                       "34-hour restart (70-hr cycle reached)")
        elif c.driving_left() <= EPS or c.window_left() <= EPS:
            reason = "11-hr driving limit" if c.driving_left() <= EPS else "14-hr window"
            self._stop(StopType.REST, DutyStatus.SLEEPER, self.rules.required_off_duty_hours,
                       f"10-hour rest ({reason})")
        else:
            self._stop(StopType.BREAK, DutyStatus.OFF_DUTY, self.rules.break_duration_hours,
                       "30-minute break (8 hrs driving)")

    # -- primitives ----------------------------------------------------------
    def _add_stop(self, kind: StopType, hours: float) -> Stop:
        stop = Stop(
            type=kind,
            arrival=self.now,
            departure=self.now + timedelta(hours=hours),
            miles_from_start=self.miles,
            position=self.track.position_at(self.miles),
        )
        self.stops.append(stop)
        return stop

    def _stop(self, kind: StopType, status: DutyStatus, hours: float, note: str) -> None:
        stop = self._add_stop(kind, hours)
        self._segment(status, hours, note, at=stop)
        self.last_stop = stop
        if kind is StopType.FUEL:
            self.miles_since_fuel = 0.0

    def _segment(self, status: DutyStatus, hours: float, note: str, *, miles: float = 0.0,
                 at: Stop) -> None:
        start = self.now
        cycle_before = self.clock.cycle_used
        self.now = start + timedelta(hours=hours)
        self.clock.record(status, hours)
        self.segments.append(Segment(
            status=status, start=start, end=self.now, note=note, miles=miles,
            start_miles=self.miles, cycle_before=cycle_before,
            cycle_after=self.clock.cycle_used, stop=at,
        ))
        self.miles += miles
        self.miles_since_fuel += miles
