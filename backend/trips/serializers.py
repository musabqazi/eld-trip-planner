from rest_framework import serializers

from .models import Trip


class TripInputSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=255)
    pickup_location = serializers.CharField(max_length=255)
    dropoff_location = serializers.CharField(max_length=255)
    current_cycle_used = serializers.FloatField(min_value=0, max_value=70)
    start_time = serializers.DateTimeField(required=False, allow_null=True)


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ["id", "current_location", "pickup_location", "dropoff_location", "current_cycle_used", "start_time", "result", "created_at"]
        read_only_fields = fields
