"""HTTP boundary: validate requests and present results as JSON."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from django.utils import timezone
from rest_framework import serializers

from services.plan_trip import LocationInput, TripPlanResult, TripRequest


class LocationSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=255)
    lat = serializers.FloatField(required=False, allow_null=True, min_value=-90, max_value=90)
    lng = serializers.FloatField(required=False, allow_null=True, min_value=-180, max_value=180)

    def to_internal_value(self, data):
        if isinstance(data, str):  # allow plain "Chicago, IL"
            data = {"label": data}
        return super().to_internal_value(data)


class TripRequestSerializer(serializers.Serializer):
    current_location = LocationSerializer()
    pickup_location = LocationSerializer()
    dropoff_location = LocationSerializer()
    current_cycle_used = serializers.FloatField(min_value=0, max_value=70)
    start_time = serializers.DateTimeField(required=False, allow_null=True)

    def to_trip_request(self) -> TripRequest:
        d = self.validated_data
        start = d.get("start_time")
        if start is None:
            start = datetime.combine(timezone.localdate(), time(8, 0))
        # Logs are kept in home-terminal local time; drop tz info after conversion.
        if timezone.is_aware(start):
            start = start.replace(tzinfo=None)
        return TripRequest(
            current=LocationInput(**d["current_location"]),
            pickup=LocationInput(**d["pickup_location"]),
            dropoff=LocationInput(**d["dropoff_location"]),
            cycle_used=d["current_cycle_used"],
            start_time=start.replace(second=0, microsecond=0),
        )


def _iso(dt: datetime) -> str:
    """Round to the nearest minute - log sheets are read to 15-min precision."""
    return (dt + timedelta(seconds=30)).replace(second=0, microsecond=0).isoformat()


def _r(value: float, digits: int = 2) -> float:
    return round(value, digits)


def present_trip_plan(result: TripPlanResult) -> dict:
    segments = result.segments
    stops = result.stops
    driving = sum(s.hours for s in segments if s.status.value == "driving")
    on_duty = sum(s.hours for s in segments if s.status.is_on_duty)
    count = lambda kind: sum(1 for s in stops if s.type.value == kind)  # noqa: E731

    return {
        "places": {
            key: {"label": p.label, "lat": p.lat, "lng": p.lng} for key, p in result.places.items()
        },
        "route": {
            "distance_miles": _r(result.route.distance_miles, 1),
            "duration_hours": _r(result.route.duration_hours),
            "geometry": [[p.lat, p.lng] for p in result.geometry],
            "legs": [
                {"distance_miles": _r(l.distance_miles, 1), "duration_hours": _r(l.duration_hours)}
                for l in result.route.legs
            ],
        },
        "stops": [
            {
                "id": i,
                "type": s.type.value,
                "label": s.label,
                "lat": s.position.lat,
                "lng": s.position.lng,
                "arrival": _iso(s.arrival),
                "departure": _iso(s.departure),
                "duration_hours": _r(s.duration_hours),
                "miles_from_start": _r(s.miles_from_start, 1),
            }
            for i, s in enumerate(stops)
        ],
        "segments": [
            {
                "status": s.status.value,
                "start": _iso(s.start),
                "end": _iso(s.end),
                "hours": _r(s.hours),
                "miles": _r(s.miles, 1),
                "note": s.note,
                "location": s.stop.label if s.stop else "",
            }
            for s in segments
        ],
        "daily_logs": [
            {
                "date": log.date.isoformat(),
                "day_number": log.day_number,
                "from_location": log.from_location,
                "to_location": log.to_location,
                "total_miles": log.total_miles,
                "totals": log.totals,
                "entries": [
                    {"status": e.status.value, "start_hour": _r(e.start_hour, 4), "end_hour": _r(e.end_hour, 4)}
                    for e in log.entries
                ],
                "remarks": [
                    {"hour": _r(r.hour, 4), "status": r.status.value, "location": r.location, "note": r.note}
                    for r in log.remarks
                ],
                "recap": {
                    "on_duty_today": log.on_duty_today,
                    "cycle_used": log.cycle_used,
                    "cycle_available": log.cycle_available,
                    "restart_taken": log.restart_taken,
                },
            }
            for log in result.daily_logs
        ],
        "summary": {
            "total_miles": _r(result.route.distance_miles, 1),
            "driving_hours": _r(driving),
            "on_duty_hours": _r(on_duty),
            "trip_start": _iso(segments[0].start) if segments else None,
            "trip_end": _iso(segments[-1].end) if segments else None,
            "total_trip_hours": _r(sum(s.hours for s in segments)),
            "days": len(result.daily_logs),
            "fuel_stops": count("fuel"),
            "breaks": count("break"),
            "rests": count("rest"),
            "restarts": count("restart"),
            "cycle_used_start": result.request.cycle_used,
        },
    }


class PlaceSerializer(serializers.Serializer):
    label = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
