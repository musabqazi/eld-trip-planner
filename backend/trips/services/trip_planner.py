"""Orchestrates geocoding, routing, HOS planning and log generation for one trip."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from .daily_logs import build_daily_logs
from .geocoding import Place, geocode
from .hos_planner import HOSPlanner, Leg
from .routing import Route, route_between


def _round_to_quarter(dt: datetime) -> datetime:
    minute = (dt.minute // 15) * 15
    return dt.replace(minute=minute, second=0, microsecond=0)


def plan_trip(
    current_location: str,
    pickup_location: str,
    dropoff_location: str,
    current_cycle_used: float,
    start_time: Optional[datetime] = None,
    *,
    places: Optional[Dict[str, Place]] = None,
    route: Optional[Route] = None,
) -> Dict:
    """
    Returns a JSON-serialisable plan. `places` and `route` can be injected
    (used by tests) to avoid network calls.
    """
    start_time = _round_to_quarter(start_time or datetime.now())

    if places is None:
        places = {
            "current": geocode(current_location),
            "pickup": geocode(pickup_location),
            "dropoff": geocode(dropoff_location),
        }
    if route is None:
        route = route_between([places["current"], places["pickup"], places["dropoff"]])

    legs = [
        Leg(
            name="to pickup",
            distance_miles=route.legs[0].distance_miles,
            duration_hours=route.legs[0].duration_hours,
            start_label=places["current"].short_name,
            end_label=places["pickup"].short_name,
        ),
        Leg(
            name="to drop-off",
            distance_miles=route.legs[1].distance_miles,
            duration_hours=route.legs[1].duration_hours,
            start_label=places["pickup"].short_name,
            end_label=places["dropoff"].short_name,
        ),
    ]

    plan = HOSPlanner(legs, start_time, current_cycle_used).plan()
    logs = build_daily_logs(plan.segments, plan.trip_start, plan.trip_end)

    stops = []
    for s in plan.stops:
        lat, lon = route.point_at_mile(s.route_miles)
        stops.append(
            {
                "kind": s.kind,
                "label": s.label,
                "start": s.start.isoformat(),
                "end": s.end.isoformat(),
                "duration_hours": round(s.duration_hours, 2),
                "route_miles": round(s.route_miles, 1),
                "lat": round(lat, 5),
                "lon": round(lon, 5),
            }
        )

    return {
        "inputs": {
            "current_location": current_location,
            "pickup_location": pickup_location,
            "dropoff_location": dropoff_location,
            "current_cycle_used": current_cycle_used,
            "start_time": start_time.isoformat(),
        },
        "places": {k: v.to_dict() for k, v in places.items()},
        "route": {
            "geometry": [[round(lat, 5), round(lon, 5)] for lat, lon in route.geometry],
            "distance_miles": route.distance_miles,
            "duration_hours": route.duration_hours,
            "legs": [
                {"name": "Start to pickup", "distance_miles": round(route.legs[0].distance_miles, 1), "duration_hours": round(route.legs[0].duration_hours, 2)},
                {"name": "Pickup to drop-off", "distance_miles": round(route.legs[1].distance_miles, 1), "duration_hours": round(route.legs[1].duration_hours, 2)},
            ],
        },
        "stops": stops,
        "summary": {
            "trip_start": plan.trip_start.isoformat(),
            "trip_end": plan.trip_end.isoformat(),
            "total_miles": plan.total_miles,
            "total_driving_hours": plan.total_driving_hours,
            "total_on_duty_hours": plan.total_on_duty_hours,
            "total_trip_hours": round((plan.trip_end - plan.trip_start).total_seconds() / 3600, 2),
            "days": plan.days,
            "cycle_hours_at_end": plan.cycle_hours_at_end,
            "fuel_stops": sum(1 for s in plan.stops if s.kind == "fuel"),
            "rest_periods": sum(1 for s in plan.stops if s.kind == "rest"),
            "breaks": sum(1 for s in plan.stops if s.kind == "break"),
            "restarts": sum(1 for s in plan.stops if s.kind == "restart"),
        },
        "assumptions": [
            "Property carrying driver, 70 hours in 8 days",
            "Up to 11 hours driving inside a 14 hour window, reset by a 10 hour rest",
            "30 minute break after 8 hours of driving",
            "34 hour restart once the 70 hours are used up",
            "Fuel stop of 30 minutes at least every 1,000 miles",
            "1 hour each for pickup and drop-off",
            "No adverse driving conditions",
        ],
        "daily_logs": logs,
    }
