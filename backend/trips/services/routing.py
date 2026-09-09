"""Free routing via the public OSRM demo server (no API key)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple

import requests
from django.conf import settings

from .geocoding import Place

METERS_PER_MILE = 1609.344


class RoutingError(Exception):
    pass


@dataclass
class RoutedLeg:
    distance_miles: float
    duration_hours: float


@dataclass
class Route:
    geometry: List[Tuple[float, float]]  # [(lat, lon), ...]
    legs: List[RoutedLeg]
    distance_miles: float
    duration_hours: float
    cumulative_miles: List[float] = field(default_factory=list)

    def point_at_mile(self, mile: float) -> Tuple[float, float]:
        """Interpolate a coordinate along the route at a given cumulative mile."""
        if not self.geometry:
            return (0.0, 0.0)
        if mile <= 0:
            return self.geometry[0]
        if mile >= self.cumulative_miles[-1]:
            return self.geometry[-1]
        lo, hi = 0, len(self.cumulative_miles) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if self.cumulative_miles[mid] < mile:
                lo = mid + 1
            else:
                hi = mid
        i = max(lo, 1)
        d0, d1 = self.cumulative_miles[i - 1], self.cumulative_miles[i]
        t = 0.0 if d1 == d0 else (mile - d0) / (d1 - d0)
        (lat0, lon0), (lat1, lon1) = self.geometry[i - 1], self.geometry[i]
        return (lat0 + (lat1 - lat0) * t, lon0 + (lon1 - lon0) * t)


def _haversine_miles(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    r = 3958.7613
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _build_route(geometry: List[Tuple[float, float]], legs: List[RoutedLeg]) -> Route:
    cumulative = [0.0]
    for i in range(1, len(geometry)):
        cumulative.append(cumulative[-1] + _haversine_miles(geometry[i - 1], geometry[i]))
    total_miles = sum(l.distance_miles for l in legs)
    # Scale the geometry mileage so it matches OSRM's road distance exactly
    if cumulative[-1] > 0 and total_miles > 0:
        k = total_miles / cumulative[-1]
        cumulative = [c * k for c in cumulative]
    return Route(
        geometry=geometry,
        legs=legs,
        distance_miles=round(total_miles, 1),
        duration_hours=round(sum(l.duration_hours for l in legs), 2),
        cumulative_miles=cumulative,
    )


def route_between(places: List[Place]) -> Route:
    if len(places) < 2:
        raise RoutingError("At least two locations are required for routing.")
    coords = ";".join(f"{p.lon},{p.lat}" for p in places)
    url = f"{settings.OSRM_URL}/{coords}"
    try:
        resp = requests.get(url, params={"overview": "full", "geometries": "geojson", "steps": "false"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise RoutingError(f"Routing service unavailable: {exc}") from exc

    if data.get("code") != "Ok" or not data.get("routes"):
        raise RoutingError("No drivable route found between these locations. Check that they are road-connected.")

    r = data["routes"][0]
    geometry = [(lat, lon) for lon, lat in r["geometry"]["coordinates"]]
    legs = [RoutedLeg(distance_miles=l["distance"] / METERS_PER_MILE, duration_hours=l["duration"] / 3600.0) for l in r["legs"]]
    return _build_route(geometry, legs)


def straight_line_route(places: List[Place], avg_speed_mph: float = 55.0) -> Route:
    """Fallback used in tests / offline: straight lines at an average speed."""
    geometry = [(p.lat, p.lon) for p in places]
    legs = []
    for a, b in zip(places, places[1:]):
        miles = _haversine_miles((a.lat, a.lon), (b.lat, b.lon)) * 1.2  # road factor
        legs.append(RoutedLeg(distance_miles=miles, duration_hours=miles / avg_speed_mph))
    return _build_route(geometry, legs)
