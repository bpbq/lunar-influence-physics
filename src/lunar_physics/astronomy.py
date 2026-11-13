"""Astronomical geometry built on Skyfield and a fixed JPL ephemeris."""

from __future__ import annotations

import numpy as np
from skyfield.api import wgs84
from skyfield.framelib import itrs
from skyfield.positionlib import ICRF

AU_M = 149_597_870_700.0


def geometric_body_vectors_itrs(eph, times, body_name: str) -> tuple[np.ndarray, np.ndarray]:
    """Return simultaneous Earth-to-body vectors in ICRF and ITRS, metres."""
    earth_bary = eph["earth"].at(times)
    body_bary = eph[body_name].at(times)
    vector_au = body_bary.position.au - earth_bary.position.au
    vector = ICRF(vector_au, t=times, center=399)
    icrf_m = vector_au.T * AU_M
    itrs_m = vector.frame_xyz(itrs).m.T
    return icrf_m, itrs_m


def local_observables(eph, times, lat: float, lon: float, elevation_m: float, body_name: str):
    observer = eph["earth"] + wgs84.latlon(lat, lon, elevation_m=elevation_m)
    apparent = observer.at(times).observe(eph[body_name]).apparent()
    alt, az, distance = apparent.altaz()
    ra, dec, _ = apparent.radec(epoch="date")
    last_hours = times.gast + lon / 15.0
    hour_angle = (last_hours - ra.hours + 12.0) % 24.0 - 12.0
    return {
        "altitude_deg": alt.degrees,
        "azimuth_deg": az.degrees,
        "distance_m": distance.m,
        "declination_deg": dec.degrees,
        "hour_angle_hours": hour_angle,
    }


def lunar_phase(eph, times) -> dict[str, np.ndarray]:
    earth = eph["earth"].at(times).position.au
    moon = eph["moon"].at(times).position.au
    sun = eph["sun"].at(times).position.au
    moon_to_sun = sun - moon
    moon_to_earth = earth - moon
    cos_i = np.sum(moon_to_sun * moon_to_earth, axis=0)
    cos_i /= np.linalg.norm(moon_to_sun, axis=0) * np.linalg.norm(moon_to_earth, axis=0)
    phase_angle = np.arccos(np.clip(cos_i, -1.0, 1.0))

    earth_at = eph["earth"].at(times)
    moon_app = earth_at.observe(eph["moon"]).apparent()
    sun_app = earth_at.observe(eph["sun"]).apparent()
    _, moon_lon, _ = moon_app.ecliptic_latlon(epoch="date")
    _, sun_lon, _ = sun_app.ecliptic_latlon(epoch="date")
    synodic = ((moon_lon.degrees - sun_lon.degrees) % 360.0) / 360.0
    return {
        "phase_angle_deg": np.rad2deg(phase_angle),
        "synodic_phase": synodic,
        "illuminated_fraction": (1.0 + np.cos(phase_angle)) / 2.0,
    }
