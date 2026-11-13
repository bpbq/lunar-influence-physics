"""Public calculation API."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import platform

import numpy as np
import pandas as pd
import skyfield

from .astronomy import geometric_body_vectors_itrs, local_observables, lunar_phase
from .constants import GM_MOON, GM_SUN, NM_PER_M
from .ephemeris import load_ephemeris, require_reliable_eop_coverage
from .frames import enu_basis, wgs84_position
from .gravity import tidal_acceleration, tidal_potential, tidal_tensor
from .illuminance import clear_sky_horizontal_lux


def _utc(value) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        raise ValueError("start_utc and end_utc must be timezone-aware")
    return stamp.tz_convert("UTC")


def _derivative(values: np.ndarray, index: pd.DatetimeIndex) -> np.ndarray:
    if len(index) < 2:
        return np.full_like(values, np.nan, dtype=float)
    seconds = np.array([stamp.timestamp() for stamp in index], dtype=float)
    return np.gradient(values, seconds, axis=0, edge_order=1)


def calculate(lat, lon, elevation_m, start_utc, end_utc, step_minutes=15, *,
              verify_ephemeris=True, timescale_mode="builtin_snapshot", eop_path=None):
    """Calculate astronomy and rigid-Earth tidal physics on `[start, end)`."""
    start, end = _utc(start_utc), _utc(end_utc)
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError("latitude or longitude outside supported range")
    if end <= start or step_minutes <= 0:
        raise ValueError("end must follow start and step_minutes must be positive")
    supported_start = pd.Timestamp("1900-01-01T00:00:00Z")
    supported_end = pd.Timestamp("2051-01-01T00:00:00Z")
    if start < supported_start or end > supported_end:
        raise ValueError("DE421 supported UTC interval is [1900-01-01, 2051-01-01)")
    index = pd.date_range(start, end, freq=pd.Timedelta(minutes=step_minutes), inclusive="left")
    eph, ts, provenance = load_ephemeris(
        verify=verify_ephemeris, timescale_mode=timescale_mode, eop_path=eop_path,
    )
    require_reliable_eop_coverage(provenance, start, end)
    times = ts.from_datetimes(index.to_pydatetime())
    observer = wgs84_position(lat, lon, elevation_m)
    basis = enu_basis(lat, lon)
    frame = pd.DataFrame(index=index)

    vectors = {}
    totals = {"acc": np.zeros((len(index), 3)), "potential": np.zeros(len(index)),
              "tensor": np.zeros((len(index), 3, 3))}
    for name, gm in (("moon", GM_MOON), ("sun", GM_SUN)):
        icrf_m, itrs_m = geometric_body_vectors_itrs(eph, times, name)
        vectors[name] = itrs_m
        acc = tidal_acceleration(itrs_m, observer, gm)
        potential = tidal_potential(itrs_m, observer, gm)
        tensor = tidal_tensor(itrs_m, observer, gm)
        local = acc @ basis.T
        obs = local_observables(eph, times, lat, lon, elevation_m, name)
        frame[f"{name}_distance_m"] = np.linalg.norm(icrf_m, axis=1)
        for axis, values in zip("xyz", icrf_m.T):
            frame[f"{name}_geometric_icrf_{axis}_m"] = values
        for axis, values in zip("xyz", itrs_m.T):
            frame[f"{name}_geometric_itrs_{axis}_m"] = values
        frame[f"{name}_altitude_deg"] = obs["altitude_deg"]
        frame[f"{name}_azimuth_deg"] = obs["azimuth_deg"]
        if name == "moon":
            frame["moon_declination_deg"] = obs["declination_deg"]
            frame["moon_hour_angle_hours"] = obs["hour_angle_hours"]
        for axis, values in zip("xyz", acc.T):
            frame[f"{name}_tidal_itrs_{axis}_m_s2"] = values
        for axis, values in zip(("east", "north", "vertical"), local.T):
            frame[f"{name}_tidal_{axis}_m_s2"] = values
            frame[f"{name}_tidal_{axis}_nm_s2"] = values * NM_PER_M
        frame[f"{name}_tidal_magnitude_m_s2"] = np.linalg.norm(acc, axis=1)
        frame[f"{name}_tidal_potential_m2_s2"] = potential
        for i, row in enumerate("enu"):
            for j, col in enumerate("enu"):
                local_tensor = np.einsum("ij,njk,lk->nil", basis, tensor, basis)
                frame[f"{name}_tidal_tensor_{row}{col}_s-2"] = local_tensor[:, i, j]
        totals["acc"] += acc
        totals["potential"] += potential
        totals["tensor"] += tensor

    total_local = totals["acc"] @ basis.T
    for axis, values in zip("xyz", totals["acc"].T):
        frame[f"total_tidal_itrs_{axis}_m_s2"] = values
        frame[f"total_tidal_itrs_{axis}_derivative_m_s3"] = _derivative(values, index)
    for axis, values in zip(("east", "north", "vertical"), total_local.T):
        frame[f"total_tidal_{axis}_m_s2"] = values
        frame[f"total_tidal_{axis}_nm_s2"] = values * NM_PER_M
        frame[f"total_tidal_{axis}_derivative_m_s3"] = _derivative(values, index)
    frame["total_tidal_magnitude_m_s2"] = np.linalg.norm(totals["acc"], axis=1)
    frame["total_tidal_potential_m2_s2"] = totals["potential"]
    total_local_tensor = np.einsum("ij,njk,lk->nil", basis, totals["tensor"], basis)
    for i, row in enumerate("enu"):
        for j, col in enumerate("enu"):
            frame[f"total_tidal_tensor_{row}{col}_s-2"] = total_local_tensor[:, i, j]

    phase = lunar_phase(eph, times)
    for key, values in phase.items():
        frame[f"moon_{key}"] = values
    frame["moon_outdoor_illuminance_lux"] = clear_sky_horizontal_lux(
        phase["phase_angle_deg"], frame["moon_distance_m"], frame["moon_altitude_deg"]
    )
    frame.index.name = "time_utc"
    frame.attrs["metadata"] = {
        **provenance,
        "model": "rigid-earth-exact-differential-tide-v0.1",
        "coordinates": "WGS84 geodetic; ITRS and local ENU",
        "lat_deg": lat, "lon_deg": lon, "elevation_m_ellipsoidal": elevation_m,
        "step_minutes": step_minutes, "skyfield_version": skyfield.__version__,
        "skyfield_data_version": importlib.metadata.version("skyfield-data"),
        "gm_moon_m3_s2": GM_MOON, "gm_sun_m3_s2": GM_SUN,
        "python_version": platform.python_version(), "generated_utc": datetime.now(timezone.utc).isoformat(),
        "illuminance_model": "Krisciunas-Schaefer phase + clear-sky extinction; outdoor horizontal",
    }
    return frame
