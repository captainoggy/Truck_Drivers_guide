"""DriverClock: the single source of truth for HOS counters.

Every duty-status change goes through one of the mutating methods, and the
planner asks the clock how much legal driving time remains.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import DutyStatus
from .rules import HOSRules


@dataclass
class DriverClock:
    rules: HOSRules
    cycle_used: float = 0.0            # on-duty hours in the rolling 70h/8d cycle
    driving_in_shift: float = 0.0      # toward the 11-hour limit
    window_elapsed: float = 0.0        # toward the 14-hour window
    window_open: bool = False
    driving_since_break: float = 0.0   # toward the 8-hour break rule
    consecutive_off: float = 0.0       # current run of non-working time

    # -- queries -----------------------------------------------------------
    def driving_left(self) -> float:
        return self.rules.max_driving_hours - self.driving_in_shift

    def window_left(self) -> float:
        return self.rules.driving_window_hours - self.window_elapsed

    def until_break(self) -> float:
        return self.rules.break_after_driving_hours - self.driving_since_break

    def cycle_left(self) -> float:
        return self.rules.cycle_limit_hours - self.cycle_used

    def max_drive_hours(self) -> float:
        return max(0.0, min(self.driving_left(), self.window_left(),
                            self.until_break(), self.cycle_left()))

    # -- transitions -------------------------------------------------------
    def record(self, status: DutyStatus, hours: float) -> None:
        if hours <= 0:
            return
        if status.is_on_duty:
            self.window_open = True
            self.cycle_used += hours
            self.consecutive_off = 0.0
        else:
            self.consecutive_off += hours

        if self.window_open:
            self.window_elapsed += hours

        if status is DutyStatus.DRIVING:
            self.driving_in_shift += hours
            self.driving_since_break += hours
        elif hours >= self.rules.break_duration_hours - 1e-9:
            # Any 30 consecutive minutes not driving satisfies the break rule.
            self.driving_since_break = 0.0

        if self.consecutive_off >= self.rules.required_off_duty_hours - 1e-9:
            self._reset_shift()
        if self.consecutive_off >= self.rules.restart_hours - 1e-9:
            self.cycle_used = 0.0

    def _reset_shift(self) -> None:
        self.driving_in_shift = 0.0
        self.window_elapsed = 0.0
        self.window_open = False
        self.driving_since_break = 0.0
