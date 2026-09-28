"""Offline reverse geocoder: nearest US/Canadian town (GeoNames, pop >= 5,000).

Log remarks need "City, ST" for every duty-status change. Doing that over a
public API is slow and rate-limited, so we look it up locally instead.
Data: https://download.geonames.org/export/dump/cities5000.zip (CC BY 4.0).
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from hos.models import Point
from hos.track import haversine_miles

from .base import ReverseGeocoder

DATA_FILE = Path(__file__).parent / "data" / "na_cities.json"
AT_CITY_MILES = 5.0
COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


@lru_cache(maxsize=1)
def _cities() -> list[tuple[str, str, float, float]]:
    with DATA_FILE.open(encoding="utf-8") as f:
        return [(name, st, lat, lng) for name, st, lat, lng, _pop in json.load(f)]


def _bearing(frm: Point, to: Point) -> str:
    lat1, lat2 = math.radians(frm.lat), math.radians(to.lat)
    dlng = math.radians(to.lng - frm.lng)
    x = math.sin(dlng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    deg = (math.degrees(math.atan2(x, y)) + 360) % 360
    return COMPASS[int((deg + 22.5) // 45) % 8]


class NearestCityLocator(ReverseGeocoder):
    def reverse(self, point: Point) -> str | None:
        best, best_d = None, float("inf")
        cos_lat = math.cos(math.radians(point.lat))
        for city in _cities():
            # cheap equirectangular pre-filter, exact distance for the winner
            d = (city[2] - point.lat) ** 2 + ((city[3] - point.lng) * cos_lat) ** 2
            if d < best_d:
                best, best_d = city, d
        if best is None:
            return None
        name, state, lat, lng = best
        city_point = Point(lat, lng)
        miles = haversine_miles(point, city_point)
        if miles <= AT_CITY_MILES:
            return f"{name}, {state}"
        return f"{miles:.0f} mi {_bearing(city_point, point)} of {name}, {state}"
