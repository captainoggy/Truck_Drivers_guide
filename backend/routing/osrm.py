"""OSRM routing adapter (public demo server, no API key)."""
from __future__ import annotations

import hashlib

import requests
from django.conf import settings
from django.core.cache import cache

from hos.models import Point

from .base import METERS_PER_MILE, Route, RouteLeg, RoutingError, RoutingProvider

TIMEOUT = 20


class OSRMRoutingProvider(RoutingProvider):
    def __init__(self, base_url: str | None = None, session: requests.Session | None = None):
        self.base_url = (base_url or settings.OSRM_URL).rstrip("/")
        self.session = session or requests.Session()

    def route(self, waypoints: list[Point]) -> Route:
        coords = ";".join(f"{p.lng:.6f},{p.lat:.6f}" for p in waypoints)
        key = "osrm:" + hashlib.md5(coords.encode()).hexdigest()
        cached = cache.get(key)
        if cached is not None:
            return cached
        try:
            resp = self.session.get(
                f"{self.base_url}/route/v1/driving/{coords}",
                params={"overview": "full", "geometries": "geojson"},
                timeout=TIMEOUT,
            )
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            raise RoutingError("Routing service is unavailable, please try again.") from exc

        if data.get("code") != "Ok" or not data.get("routes"):
            raise RoutingError("No drivable route found between these locations.")

        best = data["routes"][0]
        route = Route(
            distance_miles=best["distance"] / METERS_PER_MILE,
            duration_hours=best["duration"] / 3600,
            geometry=[Point(lat, lng) for lng, lat in best["geometry"]["coordinates"]],
            legs=[RouteLeg(leg["distance"] / METERS_PER_MILE, leg["duration"] / 3600) for leg in best["legs"]],
        )
        cache.set(key, route, 60 * 60 * 6)
        return route
