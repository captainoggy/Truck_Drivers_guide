"""Photon (komoot) geocoder: free, key-less, OpenStreetMap based."""
from __future__ import annotations

import hashlib

import requests
from django.core.cache import cache

from .base import Geocoder, Place, RoutingError

PHOTON_URL = "https://photon.komoot.io"
TIMEOUT = 8
USER_AGENT = "TruckLogBook/1.0 (ELD trip planner)"
US_CENTER = {"lat": 39.5, "lon": -98.35}


def _format_label(props: dict) -> str:
    name = props.get("name")
    city = props.get("city") or props.get("town") or props.get("village")
    if not (name or city):
        city = props.get("county")
    state = props.get("state")
    country_code = (props.get("countrycode") or "").upper()
    parts: list[str] = []
    for part in (name, city, state):
        if part and part not in parts:
            parts.append(part)
    if country_code and country_code != "US":
        parts.append(country_code)
    return ", ".join(parts) or "Unknown location"


class PhotonGeocoder(Geocoder):
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    def search(self, query: str, limit: int = 5) -> list[Place]:
        query = query.strip()
        if not query:
            return []
        key = "photon:" + hashlib.md5(f"{limit}:{query.lower()}".encode()).hexdigest()
        cached = cache.get(key)
        if cached is not None:
            return cached
        try:
            resp = self.session.get(
                f"{PHOTON_URL}/api/",
                params={"q": query, "limit": limit, "lang": "en", **US_CENTER},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RoutingError("Geocoding service is unavailable, please try again.") from exc

        # Prefer real places (cities/towns) over POIs that merely contain the name,
        # e.g. "St. Louis, MO" should not resolve to "Washington University in St. Louis".
        features = sorted(
            resp.json().get("features", []),
            key=lambda f: f["properties"].get("osm_key") != "place",
        )
        places = []
        for feature in features:
            lng, lat = feature["geometry"]["coordinates"]
            places.append(Place(label=_format_label(feature["properties"]), lat=lat, lng=lng))
        cache.set(key, places, 60 * 60 * 24)
        return places
