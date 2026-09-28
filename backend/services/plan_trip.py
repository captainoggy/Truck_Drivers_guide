"""PlanTripService: the single use-case entry point (Service Layer / Facade).

geocode -> route -> simulate HOS -> label stops -> build daily logs
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

from hos.log_builder import LogBuilder
from hos.models import DailyLog, Segment, Stop, StopType
from hos.planner import Leg, TripPlanner
from hos.rules import PROPERTY_CARRYING_70_8, HOSRules
from hos.track import RouteTrack
from routing.base import Geocoder, Place, ReverseGeocoder, Route, RoutingProvider
from routing.factory import get_geocoder, get_reverse_geocoder, get_routing_provider

MAX_RESPONSE_POINTS = 2500


@dataclass
class LocationInput:
    label: str
    lat: float | None = None
    lng: float | None = None


@dataclass
class TripRequest:
    current: LocationInput
    pickup: LocationInput
    dropoff: LocationInput
    cycle_used: float
    start_time: datetime


@dataclass
class TripPlanResult:
    request: TripRequest
    places: dict[str, Place]
    route: Route
    geometry: list
    segments: list[Segment]
    stops: list[Stop]
    daily_logs: list[DailyLog]


class PlanTripService:
    def __init__(
        self,
        geocoder: Geocoder | None = None,
        router: RoutingProvider | None = None,
        locator: ReverseGeocoder | None = None,
        rules: HOSRules = PROPERTY_CARRYING_70_8,
    ):
        self.geocoder = geocoder or get_geocoder()
        self.router = router or get_routing_provider()
        self.locator = locator or get_reverse_geocoder()
        self.rules = rules

    def execute(self, req: TripRequest) -> TripPlanResult:
        with ThreadPoolExecutor(max_workers=3) as pool:
            current, pickup, dropoff = pool.map(self._resolve, (req.current, req.pickup, req.dropoff))

        route = self.router.route([current.point, pickup.point, dropoff.point])
        track = RouteTrack(route.geometry, route.distance_miles)
        to_pickup, to_dropoff = (Leg(l.distance_miles, l.duration_hours) for l in route.legs)

        segments, stops = TripPlanner(self.rules).plan(
            to_pickup, to_dropoff, track, req.start_time, req.cycle_used
        )
        self._label_stops(stops, current, pickup, dropoff)
        logs = LogBuilder(self.rules).build(segments, stops, req.cycle_used)

        return TripPlanResult(
            request=req,
            places={"current": current, "pickup": pickup, "dropoff": dropoff},
            route=route,
            geometry=_downsample(route.geometry, MAX_RESPONSE_POINTS),
            segments=segments,
            stops=stops,
            daily_logs=logs,
        )

    def _resolve(self, loc: LocationInput) -> Place:
        if loc.lat is not None and loc.lng is not None:
            return Place(label=loc.label, lat=loc.lat, lng=loc.lng)
        return self.geocoder.geocode(loc.label)

    def _label_stops(self, stops: list[Stop], current: Place, pickup: Place, dropoff: Place) -> None:
        known = {StopType.START: current, StopType.PICKUP: pickup, StopType.DROPOFF: dropoff}
        for stop in stops:
            if stop.type in known:
                stop.label = known[stop.type].label
            else:
                label = self.locator.reverse(stop.position)
                stop.label = label or f"Mile {stop.miles_from_start:,.0f} en route"


def _downsample(points: list, limit: int) -> list:
    if len(points) <= limit:
        return points
    step = len(points) / limit
    sampled = [points[int(i * step)] for i in range(limit)]
    sampled.append(points[-1])
    return sampled
