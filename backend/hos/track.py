"""RouteTrack: maps "miles travelled" to a lat/lng on the route polyline."""
from __future__ import annotations

import bisect
import math

from .models import Point

EARTH_RADIUS_MI = 3958.8


def haversine_miles(a: Point, b: Point) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlng = math.radians(b.lng - a.lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


class RouteTrack:
    def __init__(self, points: list[Point], total_miles: float | None = None):
        if not points:
            raise ValueError("RouteTrack needs at least one point")
        self.points = points
        cumulative = [0.0]
        for a, b in zip(points, points[1:]):
            cumulative.append(cumulative[-1] + haversine_miles(a, b))
        # Scale straight-line sums to the router's road distance so that
        # "mile 500" on the planner lands at mile 500 of the drawn route.
        geometric = cumulative[-1]
        scale = (total_miles / geometric) if total_miles and geometric > 0 else 1.0
        self.cumulative = [c * scale for c in cumulative]

    @property
    def total_miles(self) -> float:
        return self.cumulative[-1]

    def position_at(self, miles: float) -> Point:
        if miles <= 0 or len(self.points) == 1:
            return self.points[0]
        if miles >= self.cumulative[-1]:
            return self.points[-1]
        i = bisect.bisect_right(self.cumulative, miles)
        a, b = self.points[i - 1], self.points[i]
        span = self.cumulative[i] - self.cumulative[i - 1]
        t = (miles - self.cumulative[i - 1]) / span if span else 0.0
        return Point(a.lat + (b.lat - a.lat) * t, a.lng + (b.lng - a.lng) * t)
