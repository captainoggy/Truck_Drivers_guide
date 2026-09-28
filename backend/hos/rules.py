"""Hours-of-Service limits for a property-carrying driver (FMCSA 49 CFR 395).

Kept as a frozen config object so the planner never hard-codes a number and
tests can exercise alternative limits (e.g. the 60-hour/7-day cycle).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class HOSRules:
    max_driving_hours: float = 11.0        # per shift, after 10h off
    driving_window_hours: float = 14.0     # no driving after the 14th hour on duty
    break_after_driving_hours: float = 8.0  # 30-min break after 8h cumulative driving
    break_duration_hours: float = 0.5
    required_off_duty_hours: float = 10.0  # consecutive off to reset 11/14
    cycle_limit_hours: float = 70.0        # 70 hours / 8 days
    cycle_days: int = 8
    restart_hours: float = 34.0            # 34-hour restart resets the cycle

    # Trip assumptions from the assessment brief
    fuel_interval_miles: float = 1000.0
    fuel_stop_hours: float = 0.5
    pickup_hours: float = 1.0
    dropoff_hours: float = 1.0


PROPERTY_CARRYING_70_8 = HOSRules()
