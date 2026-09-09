from django.db import models


class Trip(models.Model):
    """A planned trip. Inputs are stored alongside the computed plan for history."""

    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_used = models.FloatField(default=0)
    start_time = models.DateTimeField()
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.current_location} → {self.pickup_location} → {self.dropoff_location}"
