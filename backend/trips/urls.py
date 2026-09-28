from django.urls import path

from .views import GeocodeView, HealthView, TripPlanView

urlpatterns = [
    path("trips/plan/", TripPlanView.as_view(), name="trip-plan"),
    path("geocode/", GeocodeView.as_view(), name="geocode"),
    path("health/", HealthView.as_view(), name="health"),
]
