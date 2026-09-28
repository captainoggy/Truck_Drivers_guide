"""Factory so callers depend on interfaces, not concrete providers."""
from .base import Geocoder, ReverseGeocoder, RoutingProvider
from .city_locator import NearestCityLocator
from .osrm import OSRMRoutingProvider
from .photon import PhotonGeocoder


def get_geocoder() -> Geocoder:
    return PhotonGeocoder()


def get_reverse_geocoder() -> ReverseGeocoder:
    return NearestCityLocator()


def get_routing_provider() -> RoutingProvider:
    return OSRMRoutingProvider()
