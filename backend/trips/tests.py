from datetime import datetime

from django.test import TestCase

from .services.geocoding import Place
from .services.hos_planner import (
    BREAK_AFTER_DRIVING_HOURS,
    DRIVING,
    MAX_DRIVING_HOURS,
    OFF_DUTY,
    ON_DUTY,
    SLEEPER,
    HOSPlanner,
    Leg,
)
from .services.routing import straight_line_route
from .services.trip_planner import plan_trip


def _legs(miles1, miles2, mph=55):
    return [
        Leg("to pickup", miles1, miles1 / mph, "A", "B"),
        Leg("to drop-off", miles2, miles2 / mph, "B", "C"),
    ]


class HOSPlannerTests(TestCase):
    def setUp(self):
        self.start = datetime(2026, 9, 8, 8, 0)

    def test_short_trip_has_no_rest(self):
        plan = HOSPlanner(_legs(100, 100), self.start, 0).plan()
        kinds = [s.kind for s in plan.stops]
        self.assertEqual(kinds, ["start", "pickup", "dropoff"])
        self.assertEqual(plan.days, 1)

    def test_break_after_eight_hours_driving(self):
        plan = HOSPlanner(_legs(20, 600), self.start, 0).plan()
        driving_before_break = 0.0
        for seg in plan.segments:
            if seg.status == DRIVING:
                driving_before_break += seg.hours
                self.assertLessEqual(driving_before_break, BREAK_AFTER_DRIVING_HOURS + 1e-6)
            elif seg.hours >= 0.5:
                driving_before_break = 0.0
        self.assertIn("break", [s.kind for s in plan.stops])

    def test_never_exceeds_eleven_hours_driving_per_window(self):
        plan = HOSPlanner(_legs(300, 2000), self.start, 0).plan()
        drive = 0.0
        for seg in plan.segments:
            if seg.status == DRIVING:
                drive += seg.hours
                self.assertLessEqual(drive, MAX_DRIVING_HOURS + 1e-6)
            elif seg.status in (SLEEPER, OFF_DUTY) and seg.hours >= 10:
                drive = 0.0
        self.assertGreaterEqual(sum(1 for s in plan.stops if s.kind == "rest"), 3)

    def test_fuel_every_thousand_miles(self):
        plan = HOSPlanner(_legs(500, 2000), self.start, 0).plan()
        fuel_stops = [s for s in plan.stops if s.kind == "fuel"]
        self.assertEqual(len(fuel_stops), 2)
        for i, s in enumerate(fuel_stops, start=1):
            self.assertAlmostEqual(s.route_miles, 1000 * i, delta=1)

    def test_cycle_limit_triggers_restart(self):
        plan = HOSPlanner(_legs(200, 1500), self.start, 65).plan()
        self.assertIn("restart", [s.kind for s in plan.stops])
        self.assertLess(plan.cycle_hours_at_end, 70)

    def test_pickup_and_dropoff_are_one_hour(self):
        plan = HOSPlanner(_legs(50, 50), self.start, 0).plan()
        on_duty = [s for s in plan.segments if s.status == ON_DUTY]
        self.assertEqual(len(on_duty), 2)
        self.assertTrue(all(abs(s.hours - 1.0) < 1e-6 for s in on_duty))


class TripPlanTests(TestCase):
    def test_daily_logs_sum_to_24_hours(self):
        places = {
            "current": Place("Chicago", "Chicago, Cook County, Illinois, United States", 41.8781, -87.6298),
            "pickup": Place("Denver", "Denver, Denver County, Colorado, United States", 39.7392, -104.9903),
            "dropoff": Place("Los Angeles", "Los Angeles, LA County, California, United States", 34.0522, -118.2437),
        }
        route = straight_line_route([places["current"], places["pickup"], places["dropoff"]])
        result = plan_trip("Chicago", "Denver", "Los Angeles", 10, datetime(2026, 9, 8, 6, 0), places=places, route=route)
        self.assertGreater(len(result["daily_logs"]), 2)
        for log in result["daily_logs"]:
            self.assertAlmostEqual(log["total_hours"], 24.0, places=1)
            # segments must be contiguous
            prev = 0.0
            for seg in log["segments"]:
                self.assertAlmostEqual(seg["start_hour"], prev, places=3)
                prev = seg["end_hour"]
            self.assertAlmostEqual(prev, 24.0, places=3)
        total_log_miles = sum(l["miles_driven"] for l in result["daily_logs"])
        self.assertAlmostEqual(total_log_miles, result["summary"]["total_miles"], delta=2)
        self.assertEqual(result["stops"][0]["kind"], "start")
        self.assertEqual(result["stops"][-1]["kind"], "dropoff")
        # every stop has a coordinate on the route
        for s in result["stops"]:
            self.assertTrue(-90 <= s["lat"] <= 90 and -180 <= s["lon"] <= 180)


class TripApiTests(TestCase):
    """HTTP contract of POST /api/trips/ with the external services stubbed out."""

    def _places(self):
        return {
            "current": Place("Chicago, IL", "Chicago, Cook County, Illinois, United States", 41.8781, -87.6298),
            "pickup": Place("Denver, CO", "Denver, Denver County, Colorado, United States", 39.7392, -104.9903),
            "dropoff": Place("Los Angeles, CA", "Los Angeles, LA County, California, United States", 34.0522, -118.2437),
        }

    def test_unknown_place_returns_readable_400(self):
        from unittest import mock

        from .services.geocoding import GeocodingError

        with mock.patch("trips.views.plan_trip", side_effect=GeocodingError("Could not find a location for “asdfqwerty”.")):
            resp = self.client.post("/api/trips/", {"current_location": "asdfqwerty", "pickup_location": "Denver, CO", "dropoff_location": "Los Angeles, CA", "current_cycle_used": 0}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("asdfqwerty", resp.json()["detail"])

    def test_cycle_used_over_70_is_rejected(self):
        resp = self.client.post("/api/trips/", {"current_location": "A", "pickup_location": "B", "dropoff_location": "C", "current_cycle_used": 90}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_plan_is_returned_and_stored(self):
        from unittest import mock

        from .models import Trip

        places = self._places()
        route = straight_line_route([places["current"], places["pickup"], places["dropoff"]])
        real = plan_trip
        with mock.patch("trips.views.plan_trip", side_effect=lambda **kw: real(**kw, places=places, route=route)):
            resp = self.client.post("/api/trips/", {"current_location": "Chicago, IL", "pickup_location": "Denver, CO", "dropoff_location": "Los Angeles, CA", "current_cycle_used": 20, "start_time": "2026-09-08T06:00:00"}, content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["result"]["summary"]["fuel_stops"], 2)
        self.assertGreaterEqual(len(body["result"]["daily_logs"]), 3)
        self.assertEqual(Trip.objects.count(), 1)
        self.assertEqual(self.client.get("/").json()["status"], "ok")
