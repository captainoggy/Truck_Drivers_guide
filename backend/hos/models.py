"""Plain dataclasses describing a planned trip. No Django imports."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class DutyStatus(str, Enum):
    OFF_DUTY = "off_duty"
    SLEEPER = "sleeper_berth"
    DRIVING = "driving"
    ON_DUTY = "on_duty"

    @property
    def is_on_duty(self) -> bool:
        return self in (DutyStatus.DRIVING, DutyStatus.ON_DUTY)


class StopType(str, Enum):
    START = "start"
    PICKUP = "pickup"
    DROPOFF = "dropoff"
    FUEL = "fuel"
    BREAK = "break"          # 30-minute break
    REST = "rest"            # 10-hour off duty (sleeper berth)
    RESTART = "restart"      # 34-hour cycle restart


@dataclass
class Point:
    lat: float
    lng: float


@dataclass
class Stop:
    type: StopType
    arrival: datetime
    departure: datetime
    miles_from_start: float
    position: Point
    label: str = ""

    @property
    def duration_hours(self) -> float:
        return (self.departure - self.arrival).total_seconds() / 3600


@dataclass
class Segment:
    """A continuous period in one duty status."""

    status: DutyStatus
    start: datetime
    end: datetime
    note: str
    miles: float = 0.0
    start_miles: float = 0.0          # odometer from trip start
    cycle_before: float = 0.0         # 70h cycle hours used when segment began
    cycle_after: float = 0.0
    stop: Stop | None = None          # where this segment starts (driving: last stop)

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600


@dataclass
class LogEntry:
    status: DutyStatus
    start_hour: float                 # 0..24 within the log day
    end_hour: float


@dataclass
class Remark:
    hour: float
    status: DutyStatus
    location: str
    note: str


@dataclass
class DailyLog:
    date: date
    day_number: int
    entries: list[LogEntry] = field(default_factory=list)
    remarks: list[Remark] = field(default_factory=list)
    totals: dict[str, float] = field(default_factory=dict)
    total_miles: float = 0.0
    from_location: str = ""
    to_location: str = ""
    on_duty_today: float = 0.0
    cycle_used: float = 0.0           # recap A: on-duty hours in current cycle
    cycle_available: float = 0.0      # recap B: 70 - A
    restart_taken: bool = False


@dataclass
class TripPlan:
    segments: list[Segment]
    stops: list[Stop]
    daily_logs: list[DailyLog]
