from django.db import DatabaseError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Trip
from .serializers import TripInputSerializer, TripSerializer
from .services.geocoding import GeocodingError
from .services.routing import RoutingError
from .services.trip_planner import plan_trip


class TripListCreateView(APIView):
    """POST trip inputs → full plan (route, stops, daily logs). GET → recent trips."""

    def get(self, request):
        trips = Trip.objects.all()[:20]
        return Response(TripSerializer(trips, many=True).data)

    def post(self, request):
        serializer = TripInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            result = plan_trip(
                current_location=data["current_location"],
                pickup_location=data["pickup_location"],
                dropoff_location=data["dropoff_location"],
                current_cycle_used=data["current_cycle_used"],
                start_time=data.get("start_time"),
            )
        except (GeocodingError, RoutingError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        trip = Trip(
            current_location=data["current_location"],
            pickup_location=data["pickup_location"],
            dropoff_location=data["dropoff_location"],
            current_cycle_used=data["current_cycle_used"],
            start_time=result["inputs"]["start_time"],
            result=result,
        )
        try:
            trip.save()
        except DatabaseError:
            # Trip history is a convenience only (ephemeral SQLite on serverless hosts).
            # A storage problem must never hide a correctly computed plan.
            pass
        return Response(TripSerializer(trip).data, status=status.HTTP_201_CREATED)


class TripDetailView(APIView):
    def get(self, request, pk: int):
        try:
            trip = Trip.objects.get(pk=pk)
        except Trip.DoesNotExist:
            return Response({"detail": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(TripSerializer(trip).data)
