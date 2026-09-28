"""Provider interfaces. Concrete adapters wrap free public map APIs."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from hos.models import Point

METERS_PER_MILE = 1609.344


class RoutingError(Exception):
    """Raised when a location can't be found or a route can't be built."""


@dataclass
class Place:
    label: str
    lat: float
    lng: float

    @property
    def point(self) -> Point:
        return Point(self.lat, self.lng)


@dataclass
class RouteLeg:
    distance_miles: float
    duration_hours: float


@dataclass
class Route:
    distance_miles: float
    duration_hours: float
    geometry: list[Point]
    legs: list[RouteLeg] = field(default_factory=list)


class Geocoder(ABC):
    """Forward geocoding: free text -> coordinates."""

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[Place]: ...

    def geocode(self, query: str) -> Place:
        results = self.search(query, limit=5)
        if not results:
            raise RoutingError(f"Could not find location: {query!r}")
        return results[0]


class ReverseGeocoder(ABC):
    """Coordinates -> short human label ("Amarillo, TX") for log remarks."""

    @abstractmethod
    def reverse(self, point: Point) -> str | None: ...


class RoutingProvider(ABC):
    @abstractmethod
    def route(self, waypoints: list[Point]) -> Route: ...
