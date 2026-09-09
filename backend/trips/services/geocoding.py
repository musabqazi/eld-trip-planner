"""Free geocoding via OpenStreetMap Nominatim (no API key)."""
from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings


class GeocodingError(Exception):
    pass


@dataclass
class Place:
    query: str
    display_name: str
    lat: float
    lon: float

    @property
    def short_name(self) -> str:
        # "Dallas, Dallas County, Texas, United States" -> "Dallas, Texas"
        parts = [p.strip() for p in self.display_name.split(",")]
        if len(parts) >= 3:
            return f"{parts[0]}, {parts[-2]}"
        return self.display_name

    def to_dict(self) -> dict:
        return {"query": self.query, "name": self.short_name, "display_name": self.display_name, "lat": self.lat, "lon": self.lon}


def geocode(query: str) -> Place:
    query = (query or "").strip()
    if not query:
        raise GeocodingError("Location is required.")
    try:
        resp = requests.get(
            settings.NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "addressdetails": 0},
            headers={"User-Agent": settings.GEOCODER_USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json()
    except requests.RequestException as exc:
        raise GeocodingError(f"Geocoding service unavailable: {exc}") from exc

    if not results:
        raise GeocodingError(f"Could not find a location for “{query}”. Try adding a state or country.")
    r = results[0]
    return Place(query=query, display_name=r.get("display_name", query), lat=float(r["lat"]), lon=float(r["lon"]))
