"""
Turns a flat list of duty segments into one Driver's Daily Log per calendar day.

Each log sheet mirrors the FMCSA paper RODS: a 24-hour grid with four lines
(Off Duty, Sleeper Berth, Driving, On Duty Not Driving), total hours per line
(which must sum to 24), miles driven that day, and remarks listing where each
change of duty status occurred.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from .hos_planner import DRIVING, OFF_DUTY, ON_DUTY, SLEEPER, Segment

STATUS_ORDER = [OFF_DUTY, SLEEPER, DRIVING, ON_DUTY]


def _hour_of_day(dt: datetime, day_start: datetime) -> float:
    return (dt - day_start).total_seconds() / 3600.0


def build_daily_logs(segments: List[Segment], trip_start: datetime, trip_end: datetime) -> List[Dict]:
    if not segments:
        return []

    first_day = trip_start.replace(hour=0, minute=0, second=0, microsecond=0)
    last_day = trip_end.replace(hour=0, minute=0, second=0, microsecond=0)
    logs: List[Dict] = []
    day = first_day
    day_index = 1

    while day <= last_day:
        day_end = day + timedelta(days=1)
        day_segments: List[Dict] = []

        # Off duty before the trip starts on day 1
        if day == first_day and trip_start > day:
            day_segments.append(
                {
                    "status": OFF_DUTY,
                    "start_hour": 0.0,
                    "end_hour": round(_hour_of_day(trip_start, day), 4),
                    "remark": "Off duty",
                    "miles": 0.0,
                }
            )

        for seg in segments:
            s = max(seg.start, day)
            e = min(seg.end, day_end)
            if e <= s:
                continue
            frac = (e - s).total_seconds() / max((seg.end - seg.start).total_seconds(), 1)
            day_segments.append(
                {
                    "status": seg.status,
                    "start_hour": round(_hour_of_day(s, day), 4),
                    "end_hour": round(_hour_of_day(e, day), 4),
                    "remark": seg.remark,
                    "miles": round(seg.miles * frac, 1),
                    "route_miles": round(seg.location_miles, 1),
                }
            )

        # Off duty after the trip ends on the last day
        if day == last_day and trip_end < day_end:
            day_segments.append(
                {
                    "status": OFF_DUTY,
                    "start_hour": round(_hour_of_day(trip_end, day), 4),
                    "end_hour": 24.0,
                    "remark": "Off duty, trip complete",
                    "miles": 0.0,
                }
            )

        totals = {status: 0.0 for status in STATUS_ORDER}
        for ds in day_segments:
            totals[ds["status"]] += ds["end_hour"] - ds["start_hour"]
        totals = {k: round(v, 2) for k, v in totals.items()}

        # Remarks: one entry per duty-status change, with the time it happened
        remarks = []
        prev_status = None
        for ds in day_segments:
            if ds["status"] != prev_status:
                remarks.append({"hour": ds["start_hour"], "text": ds["remark"]})
                prev_status = ds["status"]

        logs.append(
            {
                "day": day_index,
                "date": day.date().isoformat(),
                "segments": day_segments,
                "totals": totals,
                "total_hours": round(sum(totals.values()), 2),
                "miles_driven": round(sum(ds["miles"] for ds in day_segments if ds["status"] == DRIVING), 1),
                "remarks": remarks,
            }
        )
        day += timedelta(days=1)
        day_index += 1

    return logs
