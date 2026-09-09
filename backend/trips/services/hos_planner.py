"""
Hours-of-Service planner for a property-carrying driver.

Rules implemented (49 CFR Part 395, per the FMCSA Interstate Truck Driver's Guide):
  * 11-hour driving limit within a 14-hour driving window (§395.3(a)(2)-(3))
  * 30-minute break required after 8 cumulative hours of driving (§395.3(a)(3)(ii))
  * 10 consecutive hours off duty / sleeper berth to reset the 11 & 14-hour clocks
  * 70-hour / 8-day on-duty limit (§395.3(b)); 34-hour restart resets it (§395.3(c))
  * No adverse-driving-conditions extension (assessment assumption)

Assessment assumptions:
  * Fuel stop (30 min, on duty) at least once every 1,000 miles
  * 1 hour on duty (not driving) for pickup and for drop-off

The planner walks the route mile by mile in chunks, always driving the
largest legal block before the next required stop, and emits a flat list of
duty-status segments plus a list of stops. The daily log builder then slices
those segments at midnight boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

# Duty statuses use the four lines of a paper log grid.
OFF_DUTY = "off_duty"
SLEEPER = "sleeper_berth"
DRIVING = "driving"
ON_DUTY = "on_duty"

MAX_DRIVING_HOURS = 11.0
MAX_WINDOW_HOURS = 14.0
BREAK_AFTER_DRIVING_HOURS = 8.0
BREAK_HOURS = 0.5
DAILY_REST_HOURS = 10.0
CYCLE_LIMIT_HOURS = 70.0
RESTART_HOURS = 34.0
FUEL_INTERVAL_MILES = 1000.0
FUEL_STOP_HOURS = 0.5
PICKUP_HOURS = 1.0
DROPOFF_HOURS = 1.0
PRE_TRIP_HOURS = 0.0  # kept at 0 to match the assessment's stated assumptions

EPS = 1e-6


@dataclass
class Leg:
    """One routed leg between two named points."""

    name: str  # e.g. "Current location -> Pickup"
    distance_miles: float
    duration_hours: float
    start_label: str
    end_label: str

    @property
    def speed_mph(self) -> float:
        if self.duration_hours <= 0:
            return 55.0
        return self.distance_miles / self.duration_hours


@dataclass
class Segment:
    status: str
    start: datetime
    end: datetime
    remark: str
    location_miles: float  # cumulative miles along the full route where the segment starts
    miles: float = 0.0  # miles driven during this segment (driving only)

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0


@dataclass
class Stop:
    kind: str  # start | pickup | dropoff | fuel | break | rest | restart
    label: str
    start: datetime
    end: datetime
    route_miles: float

    @property
    def duration_hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0


@dataclass
class PlanResult:
    segments: List[Segment]
    stops: List[Stop]
    total_miles: float
    total_driving_hours: float
    total_on_duty_hours: float
    trip_start: datetime
    trip_end: datetime
    cycle_hours_at_end: float
    days: int
    violations: List[str] = field(default_factory=list)


class HOSPlanner:
    def __init__(self, legs: List[Leg], start_time: datetime, cycle_used_hours: float):
        self.legs = legs
        self.now = start_time
        self.cycle_used = max(0.0, float(cycle_used_hours))

        # Rolling counters for the current duty period
        self.window_start: Optional[datetime] = None
        self.driving_in_window = 0.0
        self.driving_since_break = 0.0
        self.miles_since_fuel = 0.0
        self.route_miles = 0.0

        self.segments: List[Segment] = []
        self.stops: List[Stop] = []

    # ---------------------------------------------------------------- helpers
    def _window_elapsed(self) -> float:
        if self.window_start is None:
            return 0.0
        return (self.now - self.window_start).total_seconds() / 3600.0

    def _add_segment(self, status: str, hours: float, remark: str, miles: float = 0.0) -> Segment:
        seg = Segment(
            status=status,
            start=self.now,
            end=self.now + timedelta(hours=hours),
            remark=remark,
            location_miles=self.route_miles,
            miles=miles,
        )
        self.segments.append(seg)
        self.now = seg.end
        return seg

    def _add_stop(self, kind: str, label: str, seg: Segment) -> None:
        self.stops.append(Stop(kind=kind, label=label, start=seg.start, end=seg.end, route_miles=seg.location_miles))

    def _start_window_if_needed(self) -> None:
        if self.window_start is None:
            self.window_start = self.now

    # ------------------------------------------------------------ duty blocks
    def on_duty(self, hours: float, remark: str, kind: Optional[str] = None, label: str = "") -> None:
        """On-duty, not driving (pickup, drop-off, fueling)."""
        self._start_window_if_needed()
        seg = self._add_segment(ON_DUTY, hours, remark)
        self.cycle_used += hours
        if hours >= BREAK_HOURS - EPS:
            # 30+ consecutive non-driving minutes satisfy the break requirement
            self.driving_since_break = 0.0
        if kind:
            self._add_stop(kind, label or remark, seg)

    def take_break(self) -> None:
        seg = self._add_segment(OFF_DUTY, BREAK_HOURS, "30 minute rest break")
        self.driving_since_break = 0.0
        self._add_stop("break", "30 minute break", seg)

    def daily_rest(self) -> None:
        seg = self._add_segment(SLEEPER, DAILY_REST_HOURS, "10 hour rest in sleeper berth")
        self.window_start = None
        self.driving_in_window = 0.0
        self.driving_since_break = 0.0
        self._add_stop("rest", "10 hour rest", seg)

    def restart(self) -> None:
        seg = self._add_segment(OFF_DUTY, RESTART_HOURS, "34 hour restart, 70 hour cycle reset")
        self.cycle_used = 0.0
        self.window_start = None
        self.driving_in_window = 0.0
        self.driving_since_break = 0.0
        self._add_stop("restart", "34 hour restart", seg)

    def fuel(self) -> None:
        self.on_duty(FUEL_STOP_HOURS, "Fuel stop", kind="fuel", label="Fuel stop")
        self.miles_since_fuel = 0.0

    # ---------------------------------------------------------------- driving
    def _available_drive_hours(self) -> float:
        return min(
            MAX_DRIVING_HOURS - self.driving_in_window,
            MAX_WINDOW_HOURS - self._window_elapsed(),
            BREAK_AFTER_DRIVING_HOURS - self.driving_since_break,
            CYCLE_LIMIT_HOURS - self.cycle_used,
        )

    def _rest_as_required(self) -> bool:
        """Insert whichever rest is required before driving can continue. Returns True if a rest was inserted."""
        if CYCLE_LIMIT_HOURS - self.cycle_used <= EPS:
            self.restart()
            return True
        if (MAX_DRIVING_HOURS - self.driving_in_window <= EPS) or (MAX_WINDOW_HOURS - self._window_elapsed() <= EPS):
            self.daily_rest()
            return True
        if BREAK_AFTER_DRIVING_HOURS - self.driving_since_break <= EPS:
            # If the 30-min break would push us past the 14-hour window with
            # nothing left to drive, a full rest is the better move.
            if MAX_WINDOW_HOURS - self._window_elapsed() <= BREAK_HOURS + EPS:
                self.daily_rest()
            else:
                self.take_break()
            return True
        return False

    def drive_leg(self, leg: Leg) -> None:
        remaining_miles = leg.distance_miles
        speed = leg.speed_mph
        guard = 0
        while remaining_miles > EPS and guard < 10_000:
            guard += 1
            if self._rest_as_required():
                continue

            self._start_window_if_needed()
            avail_hours = self._available_drive_hours()
            avail_miles = avail_hours * speed
            fuel_miles = FUEL_INTERVAL_MILES - self.miles_since_fuel
            chunk_miles = max(0.0, min(remaining_miles, avail_miles, fuel_miles))

            if chunk_miles <= EPS:
                # Reached the fuel interval exactly; refuel then continue.
                if fuel_miles <= EPS:
                    self.fuel()
                    continue
                # Otherwise a limit is binding; loop will insert the rest.
                if not self._rest_as_required():
                    break  # should not happen, but avoid infinite loop
                continue

            chunk_hours = chunk_miles / speed
            remark = f"Driving {leg.name}"
            self._add_segment(DRIVING, chunk_hours, remark, miles=chunk_miles)
            self.driving_in_window += chunk_hours
            self.driving_since_break += chunk_hours
            self.cycle_used += chunk_hours
            self.miles_since_fuel += chunk_miles
            self.route_miles += chunk_miles
            remaining_miles -= chunk_miles

            if remaining_miles > EPS and FUEL_INTERVAL_MILES - self.miles_since_fuel <= EPS:
                self.fuel()

    # ------------------------------------------------------------------- run
    def plan(self) -> PlanResult:
        trip_start = self.now
        if not self.legs:
            raise ValueError("At least one leg is required")

        origin = self.legs[0].start_label
        self.stops.append(Stop(kind="start", label=origin, start=self.now, end=self.now, route_miles=0.0))

        if PRE_TRIP_HOURS > 0:
            self.on_duty(PRE_TRIP_HOURS, f"Pre-trip inspection at {origin}")

        # Leg 1: current location -> pickup
        self.drive_leg(self.legs[0])
        self.on_duty(PICKUP_HOURS, f"Pickup and loading at {self.legs[0].end_label}", kind="pickup", label=self.legs[0].end_label)

        # Leg 2: pickup -> dropoff
        if len(self.legs) > 1:
            self.drive_leg(self.legs[1])
            self.on_duty(DROPOFF_HOURS, f"Drop-off and unloading at {self.legs[1].end_label}", kind="dropoff", label=self.legs[1].end_label)

        total_driving = sum(s.hours for s in self.segments if s.status == DRIVING)
        total_on_duty = sum(s.hours for s in self.segments if s.status in (DRIVING, ON_DUTY))
        days = (self.now.date() - trip_start.date()).days + 1

        return PlanResult(
            segments=self.segments,
            stops=self.stops,
            total_miles=round(self.route_miles, 1),
            total_driving_hours=round(total_driving, 2),
            total_on_duty_hours=round(total_on_duty, 2),
            trip_start=trip_start,
            trip_end=self.now,
            cycle_hours_at_end=round(self.cycle_used, 2),
            days=days,
            violations=[],
        )
