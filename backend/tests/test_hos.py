from datetime import datetime

import pytest

from hos.log_builder import LogBuilder
from hos.models import DutyStatus, Point, StopType
from hos.planner import Leg, TripPlanner
from hos.rules import PROPERTY_CARRYING_70_8 as RULES
from hos.track import RouteTrack

START = datetime(2026, 9, 28, 8, 0)


def straight_track(miles: float) -> RouteTrack:
    # ~69 miles per degree of latitude; exact scale is fixed by total_miles.
    return RouteTrack([Point(30, -97), Point(30 + miles / 69, -97)], total_miles=miles)


def plan(to_pickup_mi, to_dropoff_mi, cycle_used=0.0, mph=50.0):
    track = straight_track(to_pickup_mi + to_dropoff_mi or 1)
    segs, stops = TripPlanner().plan(
        Leg(to_pickup_mi, to_pickup_mi / mph), Leg(to_dropoff_mi, to_dropoff_mi / mph),
        track, START, cycle_used,
    )
    return segs, stops


def assert_hos_compliant(segments, start_cycle=0.0):
    """Independent re-check of every limit, replayed from the timeline."""
    driving = window = since_break = off_run = 0.0
    cycle = start_cycle
    window_open = False
    miles_since_fuel = 0.0
    for seg in segments:
        h = seg.hours
        if seg.status is DutyStatus.DRIVING:
            assert driving + h <= RULES.max_driving_hours + 1e-6, "11-hour limit exceeded"
            assert window + h <= RULES.driving_window_hours + 1e-6, "drove after 14-hour window"
            assert since_break + h <= RULES.break_after_driving_hours + 1e-6, "missed 30-min break"
            assert cycle + h <= RULES.cycle_limit_hours + 1e-6, "70-hour cycle exceeded"
            miles_since_fuel += seg.miles
            assert miles_since_fuel <= RULES.fuel_interval_miles + 1e-6, "went >1000 mi without fuel"
        if seg.stop and seg.stop.type is StopType.FUEL:
            miles_since_fuel = 0.0

        if seg.status.is_on_duty:
            window_open, off_run, cycle = True, 0.0, cycle + h
        else:
            off_run += h
        if window_open:
            window += h
        if seg.status is DutyStatus.DRIVING:
            driving += h
            since_break += h
        elif h >= 0.5 - 1e-9:
            since_break = 0.0
        if off_run >= 10 - 1e-9:
            driving = window = since_break = 0.0
            window_open = False
        if off_run >= 34 - 1e-9:
            cycle = 0.0


def test_short_trip_has_no_rest_stops():
    segs, stops = plan(100, 200)
    kinds = [s.type for s in stops]
    assert kinds == [StopType.START, StopType.PICKUP, StopType.DROPOFF]
    driving = sum(s.hours for s in segs if s.status is DutyStatus.DRIVING)
    on_duty = sum(s.hours for s in segs if s.status is DutyStatus.ON_DUTY)
    assert driving == pytest.approx(6.0)
    assert on_duty == pytest.approx(2.0)  # 1h pickup + 1h drop-off


def test_break_inserted_after_8_hours_driving():
    segs, stops = plan(450, 50)  # 9h straight to pickup
    kinds = [s.type for s in stops]
    assert StopType.BREAK in kinds
    first_break = next(s for s in stops if s.type is StopType.BREAK)
    assert first_break.miles_from_start == pytest.approx(400)
    assert_hos_compliant(segs)


def test_pickup_on_duty_counts_as_break():
    # 5h to pickup, 1h loading (non-driving), then 5h more -> no 30-min break needed
    segs, stops = plan(250, 250)
    assert StopType.BREAK not in [s.type for s in stops]
    assert_hos_compliant(segs)


def test_ten_hour_rest_after_11_hours_driving():
    segs, stops = plan(50, 700)
    rests = [s for s in stops if s.type is StopType.REST]
    assert len(rests) == 1
    assert rests[0].duration_hours == pytest.approx(10)
    assert_hos_compliant(segs)


def test_fuel_stop_every_1000_miles():
    segs, stops = plan(100, 2400)
    fuel = [s for s in stops if s.type is StopType.FUEL]
    assert len(fuel) == 2
    assert fuel[0].miles_from_start == pytest.approx(1000)
    assert fuel[1].miles_from_start == pytest.approx(2000)
    assert_hos_compliant(segs)


def test_cycle_limit_forces_34_hour_restart():
    segs, stops = plan(100, 400, cycle_used=66)
    restarts = [s for s in stops if s.type is StopType.RESTART]
    assert len(restarts) == 1
    assert restarts[0].duration_hours == pytest.approx(34)
    assert_hos_compliant(segs, start_cycle=66)


def test_cycle_fully_used_restarts_before_driving():
    segs, stops = plan(100, 100, cycle_used=70)
    assert stops[1].type is StopType.RESTART
    assert stops[1].miles_from_start == 0
    assert_hos_compliant(segs, start_cycle=70)


@pytest.mark.parametrize("to_pickup,to_dropoff,cycle", [
    (0, 3000, 0), (350, 2650, 20), (800, 1200, 45), (1200, 1500, 60), (10, 30, 69.5),
])
def test_long_trips_are_always_compliant(to_pickup, to_dropoff, cycle):
    segs, _ = plan(to_pickup, to_dropoff, cycle_used=cycle, mph=58)
    assert_hos_compliant(segs, start_cycle=cycle)
    total_miles = sum(s.miles for s in segs)
    assert total_miles == pytest.approx(to_pickup + to_dropoff)


def test_timeline_is_contiguous():
    segs, _ = plan(600, 1400)
    for a, b in zip(segs, segs[1:]):
        assert a.end == b.start


# -- daily logs ---------------------------------------------------------------

def build_logs(to_pickup, to_dropoff, cycle=0.0):
    segs, stops = plan(to_pickup, to_dropoff, cycle_used=cycle)
    for s in stops:
        s.label = f"{s.type.value} city"
    return segs, LogBuilder().build(segs, stops, cycle)


def test_every_log_sheet_covers_24_hours():
    _, logs = build_logs(300, 2200, cycle=10)
    assert len(logs) > 1
    for log in logs:
        assert sum(log.totals.values()) == pytest.approx(24, abs=0.02)
        assert log.entries[0].start_hour == 0
        assert log.entries[-1].end_hour == pytest.approx(24)
        for a, b in zip(log.entries, log.entries[1:]):
            assert a.end_hour == pytest.approx(b.start_hour)
            assert a.status is not b.status  # contiguous blocks are merged


def test_log_miles_and_hours_add_up_across_days():
    segs, logs = build_logs(300, 2200)
    assert sum(l.total_miles for l in logs) == pytest.approx(2500, abs=0.5)
    driving = sum(s.hours for s in segs if s.status is DutyStatus.DRIVING)
    assert sum(l.totals["driving"] for l in logs) == pytest.approx(driving, abs=0.05)


def test_first_day_is_off_duty_until_departure():
    _, logs = build_logs(100, 200)
    first = logs[0].entries[0]
    assert first.status is DutyStatus.OFF_DUTY
    assert first.end_hour == pytest.approx(8)  # trip starts 08:00


def test_recap_tracks_cycle():
    _, logs = build_logs(100, 200, cycle=30)
    assert len(logs) == 1
    # 6h driving + 2h on duty
    assert logs[0].on_duty_today == pytest.approx(8)
    assert logs[0].cycle_used == pytest.approx(38)
    assert logs[0].cycle_available == pytest.approx(32)


def test_remarks_record_each_duty_change_with_location():
    _, logs = build_logs(100, 200)
    notes = [r.note for r in logs[0].remarks]
    assert notes == ["Driving", "Pickup - loading", "Driving", "Drop-off - unloading"]
    assert logs[0].remarks[1].location == "pickup city"


def test_nearest_city_locator_labels():
    from routing.city_locator import NearestCityLocator
    loc = NearestCityLocator()
    assert loc.reverse(Point(35.222, -101.831)) == "Amarillo, TX"
    far = loc.reverse(Point(35.222, -102.4))
    assert far.endswith(", TX") and " mi " in far and " of " in far


def test_rest_spanning_midnight_is_noted_on_next_sheet():
    _, logs = build_logs(100, 1200)
    carried = [r for log in logs[1:] for r in log.remarks if r.note.startswith("(cont.)")]
    assert carried and all(r.hour == 0 for r in carried)
