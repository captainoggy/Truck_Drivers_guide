import pytest
from rest_framework.test import APIClient

from hos.models import Point
from routing.base import Geocoder, Place, ReverseGeocoder, Route, RouteLeg, RoutingProvider

PLACES = {
    "chicago, il": Place("Chicago, Illinois", 41.88, -87.63),
    "st louis, mo": Place("St. Louis, Missouri", 38.63, -90.2),
    "dallas, tx": Place("Dallas, Texas", 32.78, -96.8),
}


class FakeGeocoder(Geocoder):
    def search(self, query, limit=5):
        place = PLACES.get(query.lower())
        return [place] if place else []


class FakeLocator(ReverseGeocoder):
    def reverse(self, point):
        return "Somewhere, MO"


class FakeRouter(RoutingProvider):
    def route(self, waypoints):
        return Route(
            distance_miles=930,
            duration_hours=15.5,
            geometry=[Point(p.lat, p.lng) for p in waypoints],
            legs=[RouteLeg(300, 5), RouteLeg(630, 10.5)],
        )


@pytest.fixture(autouse=True)
def fake_providers(monkeypatch):
    monkeypatch.setattr("services.plan_trip.get_geocoder", FakeGeocoder)
    monkeypatch.setattr("services.plan_trip.get_routing_provider", FakeRouter)
    monkeypatch.setattr("services.plan_trip.get_reverse_geocoder", FakeLocator)
    monkeypatch.setattr("trips.views.get_geocoder", FakeGeocoder)


@pytest.fixture
def client():
    return APIClient()


def payload(**overrides):
    body = {
        "current_location": "Chicago, IL",
        "pickup_location": "St Louis, MO",
        "dropoff_location": {"label": "Dallas, TX", "lat": 32.78, "lng": -96.8},
        "current_cycle_used": 12,
        "start_time": "2026-09-28T07:00:00",
    }
    body.update(overrides)
    return body


def test_plan_trip_returns_route_stops_and_logs(client):
    resp = client.post("/api/trips/plan/", payload(), format="json")
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data["summary"]["total_miles"] == 930
    types = [s["type"] for s in data["stops"]]
    assert types[0] == "start" and types[-1] == "dropoff"
    assert "rest" in types  # 15.5h driving requires a 10-hour rest
    assert len(data["daily_logs"]) == 2
    for log in data["daily_logs"]:
        assert sum(log["totals"].values()) == pytest.approx(24, abs=0.02)
    rest = next(s for s in data["stops"] if s["type"] == "rest")
    assert rest["label"] == "Somewhere, MO"


def test_validation_rejects_cycle_over_70(client):
    resp = client.post("/api/trips/plan/", payload(current_cycle_used=71), format="json")
    assert resp.status_code == 400
    assert "current_cycle_used" in resp.json()


def test_unknown_location_returns_422(client):
    resp = client.post("/api/trips/plan/", payload(current_location="Nowhere-ville"), format="json")
    assert resp.status_code == 422
    assert "Could not find" in resp.json()["detail"]


def test_geocode_autocomplete(client):
    resp = client.get("/api/geocode/", {"q": "Dallas, TX"})
    assert resp.status_code == 200
    assert resp.json()[0]["label"] == "Dallas, Texas"
