"""Thin views: validate -> call service -> present."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.base import RoutingError
from routing.factory import get_geocoder
from services.plan_trip import PlanTripService

from .serializers import PlaceSerializer, TripRequestSerializer, present_trip_plan


class TripPlanView(APIView):
    def post(self, request):
        serializer = TripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = PlanTripService().execute(serializer.to_trip_request())
        except RoutingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        return Response(present_trip_plan(result))


class GeocodeView(APIView):
    """Location autocomplete for the trip form."""

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response([])
        try:
            places = get_geocoder().search(query, limit=6)
        except RoutingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(PlaceSerializer(places, many=True).data)


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})
