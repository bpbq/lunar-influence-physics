"""Rise, set, and twilight event calculations."""

from __future__ import annotations

import pandas as pd
from skyfield import almanac
from skyfield.api import wgs84

from .ephemeris import load_ephemeris


def find_events(lat, lon, elevation_m, start_utc, end_utc):
    """Return lunar/solar rise-set and twilight states within an interval."""
    eph, ts, provenance = load_ephemeris()
    start_dt = pd.Timestamp(start_utc)
    end_dt = pd.Timestamp(end_utc)
    if start_dt.tzinfo is None or end_dt.tzinfo is None:
        raise ValueError("event interval must use timezone-aware instants")
    start = ts.from_datetime(start_dt.to_pydatetime())
    end = ts.from_datetime(end_dt.to_pydatetime())
    observer = wgs84.latlon(lat, lon, elevation_m=elevation_m)
    output = []
    for body_name in ("moon", "sun"):
        function = almanac.risings_and_settings(eph, eph[body_name], observer)
        times, states = almanac.find_discrete(start, end, function)
        for time, state in zip(times, states):
            output.append({"time_utc": time.utc_iso(), "event": f"{body_name}_{'rise' if state else 'set'}"})
    function = almanac.dark_twilight_day(eph, observer)
    times, states = almanac.find_discrete(start, end, function)
    names = {0: "night", 1: "astronomical_twilight", 2: "nautical_twilight", 3: "civil_twilight", 4: "day"}
    for time, state in zip(times, states):
        output.append({"time_utc": time.utc_iso(), "event": names[int(state)]})
    return sorted(output, key=lambda item: item["time_utc"]), provenance
