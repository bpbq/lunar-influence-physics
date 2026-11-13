#!/usr/bin/env python3
"""DE421 versus JPL DE440s: controlled, unfitted physical sensitivity analysis.

Both ephemerides use exactly the same Skyfield timescale, WGS84 station,
GM values, tidal formula, ENU basis and sample grid. No automatic downloads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from skyfield.api import load_file

from lunar_physics.astronomy import geometric_body_vectors_itrs
from lunar_physics.constants import GM_MOON, GM_SUN
from lunar_physics.ephemeris import load_ephemeris
from lunar_physics.frames import enu_basis, wgs84_position
from lunar_physics.gravity import tidal_acceleration

DE440S_URL = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp"
DE440S_SHA256 = "c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2"
DE440S_BYTES = 32_726_016
STEP_MINUTES = 15
WINDOW_DAYS = 30
CASES = (
    ("seattle_2016", 47.6062, -122.3321, 56.0, "2016-01-22T00:00:00Z"),
    ("leticia_2016", -4.21528, -69.94056, 0.0, "2016-04-06T00:00:00Z"),
    ("sydney_2016", -33.8688, 151.2093, 0.0, "2016-07-18T00:00:00Z"),
    ("tromso_2016", 69.6492, 18.9553, 0.0, "2016-10-29T00:00:00Z"),
    ("seattle_2024", 47.6062, -122.3321, 56.0, "2024-02-29T00:00:00Z"),
    ("leticia_2024", -4.21528, -69.94056, 0.0, "2024-04-06T00:00:00Z"),
    ("sydney_2024", -33.8688, 151.2093, 0.0, "2024-07-18T00:00:00Z"),
    ("tromso_2024", 69.6492, 18.9553, 0.0, "2024-10-29T00:00:00Z"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def verified_de440s(path: Path):
    """Fail closed: never treat a kernel with an unknown hash as JPL DE440s."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing {path}; fetch manually from {DE440S_URL} and verify SHA-256"
        )
    if path.stat().st_size != DE440S_BYTES:
        raise ValueError("DE440s file size mismatch")
    actual = sha256(path)
    if actual != DE440S_SHA256:
        raise ValueError(f"DE440s SHA-256 mismatch: {actual}")
    return load_file(str(path))


def physics(eph, times, lat: float, lon: float, elevation_m: float) -> dict:
    """Use exactly LIPE's shipped geocentric vector and tidal functions."""
    observer = wgs84_position(lat, lon, elevation_m)
    up = enu_basis(lat, lon)[2]
    result = {}
    total_acc = np.zeros((len(times), 3))
    for body, gm in (("moon", GM_MOON), ("sun", GM_SUN)):
        icrf, itrs = geometric_body_vectors_itrs(eph, times, body)
        a = tidal_acceleration(itrs, observer, gm)
        total_acc += a
        result[f"{body}_distance_m"] = np.linalg.norm(icrf, axis=1)
        result[f"{body}_vertical_nm_s2"] = a @ up * 1e9
    result["total_vertical_nm_s2"] = total_acc @ up * 1e9
    result["total_vector_magnitude_nm_s2"] = np.linalg.norm(total_acc, axis=1) * 1e9
    return result


def delta_metrics(before, after) -> dict:
    d = np.asarray(after, dtype=float) - np.asarray(before, dtype=float)
    return {
        "mean_signed": float(d.mean()),
        "rms": float(np.sqrt(np.mean(d * d))),
        "max_absolute": float(np.abs(d).max()),
        "p95_absolute": float(np.quantile(np.abs(d), .95)),
    }


def _interpolated_maximum_seconds(values, i: int, step_seconds: float) -> float:
    """Parabolic peak offset; guards degenerate or boundary extrema."""
    if i <= 0 or i >= len(values) - 1:
        return float(i) * step_seconds
    left, middle, right = map(float, values[i-1:i+2])
    denominator = left - 2.0 * middle + right
    if abs(denominator) < 1e-12:
        return float(i) * step_seconds
    offset = 0.5 * (left - right) / denominator
    return (i + float(np.clip(offset, -0.5, 0.5))) * step_seconds


def peak_shift_metrics(before, after, step_seconds: float) -> dict:
    """Compare nearest corresponding local maxima within two sample steps."""
    x = np.asarray(before, float)
    y = np.asarray(after, float)
    old = np.flatnonzero((x[1:-1] > x[:-2]) & (x[1:-1] >= x[2:])) + 1
    new = np.flatnonzero((y[1:-1] > y[:-2]) & (y[1:-1] >= y[2:])) + 1
    matched = []
    for i in old:
        if len(new) == 0:
            break
        j = int(new[np.argmin(np.abs(new - i))])
        if abs(j - i) <= 2:
            matched.append(
                _interpolated_maximum_seconds(y, j, step_seconds)
                - _interpolated_maximum_seconds(x, int(i), step_seconds)
            )
    if not matched:
        return {"matched_peaks": 0, "max_absolute_seconds": None,
                "median_absolute_seconds": None}
    shift = np.abs(np.array(matched))
    return {"matched_peaks": int(len(shift)),
            "max_absolute_seconds": float(shift.max()),
            "median_absolute_seconds": float(np.median(shift))}


def run_comparison(kernel: Path, *, days=WINDOW_DAYS, minutes=STEP_MINUTES) -> dict:
    if days <= 0 or minutes <= 0:
        raise ValueError("days and minutes must be positive")
    old, ts, provenance = load_ephemeris()
    new = verified_de440s(kernel)
    report = {
        "status": "CONTROLLED_EPHEMERIS_SENSITIVITY_NOT_ABSOLUTE_ACCURACY",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "ephemerides": {
            "baseline": "de421.bsp",
            "baseline_sha256": provenance["ephemeris_sha256"],
            "candidate": "de440s.bsp",
            "candidate_sha256": DE440S_SHA256,
            "candidate_bytes": DE440S_BYTES,
            "candidate_source_url": DE440S_URL,
        },
        "controls": {
            "same_timescale_for_both": True,
            "timescale_mode": provenance["timescale_mode"],
            "timescale_sha256": provenance["earth_orientation_sha256"],
            "WGS84_same": True,
            "GM_values_same": True,
            "tidal_acceleration_formula_same": True,
            "local_geodetic_up_same": True,
            "fitted_scale_phase_lag_offset": False,
            "step_minutes": minutes,
            "window_days": days,
            "delta_sign": "DE440s minus DE421",
            "metric_units": {"distance_m": "metres", "vertical_nm_s2": "nm/s^2",
                             "total_vector_magnitude_nm_s2": "nm/s^2",
                             "peak_time_shift": "seconds"},
        },
        "cases": {},
    }
    for label, lat, lon, height, begin in CASES:
        start = pd.Timestamp(begin)
        end = start + pd.Timedelta(days=days)
        grid = pd.date_range(start, end, freq=pd.Timedelta(minutes=minutes),
                             inclusive="left")
        times = ts.from_datetimes(grid.to_pydatetime())
        before = physics(old, times, lat, lon, height)
        after = physics(new, times, lat, lon, height)
        metrics = {key: delta_metrics(before[key], after[key]) for key in before}
        peaks = {key: peak_shift_metrics(before[key], after[key], minutes * 60)
                 for key in ("moon_vertical_nm_s2", "total_vertical_nm_s2")}
        report["cases"][label] = {
            "latitude_deg": lat, "longitude_deg": lon,
            "elevation_m_ellipsoidal": height, "start_utc": begin,
            "samples": len(grid), "difference_metrics": metrics,
            "peak_time_shift": peaks,
        }
        print(
            f"{label}: Moon tide ΔRMS={metrics['moon_vertical_nm_s2']['rms']:.9g} "
            f"nm/s², total Δmax={metrics['total_vertical_nm_s2']['max_absolute']:.9g} "
            f"nm/s², Moon distance Δmax={metrics['moon_distance_m']['max_absolute']:.6g} m",
            flush=True,
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--de440s-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/de440s_comparison.json"))
    args = parser.parse_args()
    result = run_comparison(args.de440s_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
