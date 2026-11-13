"""Pinned ephemeris loading and provenance."""

from __future__ import annotations

import hashlib
import importlib.resources
import os
from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO
from pathlib import Path

import numpy as np
from skyfield.api import Loader, load_file
from skyfield.data import iers
from skyfield.timelib import Timescale

EPHEMERIS_NAME = "de421.bsp"
# Published DE421 file distributed by JPL/Skyfield.
DE421_SHA256 = "a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc"
SKYFIELD_IERS_SHA256 = "c7d7536d898dfa9f8cd43e8044ff51e108cc8289675a13fee9822010a1c4935c"
FINALS2000A_SHA256 = "d0d9c214fb11f4d1f9418f4075ec4310005f906674a0c4fa3a28232d4d9dd38d"
FINALS2000A_START_MJD = 41684.0  # 1973-01-02, the first finals2000A record.
KNOWN_LEAP_EFFECTIVE_MJD = np.array([
    42048.0, 42413.0, 42778.0, 43144.0, 43509.0, 43874.0, 44239.0,
    44786.0, 45151.0, 45516.0, 46247.0, 47161.0, 47892.0, 48257.0,
    48804.0, 49169.0, 49534.0, 50083.0, 50630.0, 51179.0, 53736.0,
    54832.0, 56109.0, 57204.0, 57754.0,
])


def ephemeris_path() -> Path:
    """Use an explicit data directory or the pinned skyfield-data wheel."""
    configured = os.environ.get("LUNAR_PHYSICS_DATA")
    if configured:
        return Path(configured) / EPHEMERIS_NAME
    return Path(importlib.resources.files("skyfield_data").joinpath("data", EPHEMERIS_NAME))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _date_from_mjd(mjd: float) -> date:
    return date(1858, 11, 17) + timedelta(days=int(mjd))


def _utc_midnight_iso(day: date) -> str:
    return datetime.combine(day, time(), tzinfo=timezone.utc).isoformat()


def _parse_and_validate_iers(data_path: Path):
    """Parse a complete, daily finals2000A history and validate its calendar."""
    raw = data_path.read_bytes()
    finals = iers.parse_x_y_dut1_from_finals_all(BytesIO(raw))
    record_lines = []
    for line in raw.splitlines():
        try:
            float(line[6:15])
            float(line[18:27])
            float(line[37:46])
            float(line[58:68])
        except (ValueError, IndexError):
            continue
        record_lines.append(line)
    if len(record_lines) != len(finals):
        raise ValueError("IERS records could not be matched to their calendar fields")
    if len(finals) < 2:
        raise ValueError("IERS file must contain at least two finals2000A records")

    utc_mjd = finals["utc_mjd"]
    if not np.all(np.isfinite(utc_mjd)):
        raise ValueError("IERS utc_mjd records must be finite")
    if utc_mjd[0] != FINALS2000A_START_MJD:
        raise ValueError(
            "IERS file is truncated: UTC/TAI reconstruction requires finals2000A "
            f"history beginning at MJD {FINALS2000A_START_MJD:.0f}"
        )
    if np.any(np.diff(utc_mjd) != 1.0):
        raise ValueError("IERS utc_mjd records must be calendar-daily and contiguous")
    for field in ("x_arcseconds", "y_arcseconds", "dut1"):
        if not np.all(np.isfinite(finals[field])):
            raise ValueError(f"IERS {field} records must be finite")

    x_flags = []
    dut1_flags = []
    for line, mjd in zip(record_lines, utc_mjd):
        if mjd != np.floor(mjd):
            raise ValueError("IERS utc_mjd records must represent UTC midnight")
        expected = _date_from_mjd(mjd)
        try:
            fields = (int(line[0:2]), int(line[2:4]), int(line[4:6]))
        except ValueError as exc:
            raise ValueError("IERS record has invalid calendar fields") from exc
        if fields != (expected.year % 100, expected.month, expected.day):
            raise ValueError(
                f"IERS calendar date does not match MJD {mjd:.0f}: "
                f"got {fields[0]:02d}-{fields[1]:02d}-{fields[2]:02d}"
            )
        x_flags.append(line[16:17])
        dut1_flags.append(line[57:58])
    if not set(x_flags + dut1_flags) <= {b"I", b"P"}:
        raise ValueError("IERS records must mark EOP values as observed I or predicted P")

    dut1_steps = np.diff(finals["dut1"])
    leap_mask = dut1_steps > 0.9
    invalid_step = ((np.abs(dut1_steps) > 0.1) & ~leap_mask) | (dut1_steps > 1.1)
    if np.any(invalid_step):
        raise ValueError("IERS DUT1 contains a nonphysical daily jump")
    detected_leaps = utc_mjd[1:][leap_mask]
    expected_leaps = KNOWN_LEAP_EFFECTIVE_MJD[
        KNOWN_LEAP_EFFECTIVE_MJD <= utc_mjd[-1]
    ]
    if not np.array_equal(detected_leaps, expected_leaps):
        raise ValueError(
            "IERS DUT1 leap-second jumps do not match the complete UTC history"
        )

    reliable = np.array([
        x_flag == b"I" and dut1_flag == b"I"
        for x_flag, dut1_flag in zip(x_flags, dut1_flags)
    ])
    if not reliable[0]:
        raise ValueError("IERS observed and predicted records must form contiguous sections")
    if np.any(~reliable):
        first_prediction = np.flatnonzero(~reliable)[0]
        if np.any(reliable[first_prediction:]):
            raise ValueError(
                "IERS observed and predicted records must form contiguous sections"
            )
    return finals, reliable


def _timescale_from_iers_file(data_path: Path) -> tuple[Timescale, dict]:
    """Build UT1, Delta T, leap seconds, and polar motion from one file."""
    if not data_path.is_file():
        raise FileNotFoundError(f"IERS file not found at {data_path}")
    finals, reliable = _parse_and_validate_iers(data_path)
    utc_mjd = finals["utc_mjd"]

    daily_tt, daily_delta_t, leap_dates, leap_offsets = iers.build_timescale_arrays(
        utc_mjd, finals["dut1"]
    )
    if len(leap_dates) == 0:
        raise ValueError(
            "IERS file does not contain enough leap-second history to build UTC"
        )
    ts = Timescale((daily_tt, daily_delta_t), leap_dates, leap_offsets)
    iers.install_polar_motion_table(ts, finals)
    reliable_indices = np.flatnonzero(reliable)
    predicted_indices = np.flatnonzero(~reliable)
    details = {
        "earth_orientation_record_count": int(len(finals)),
        "ut1_utc_first_seconds": float(finals["dut1"][0]),
        "ut1_utc_last_seconds": float(finals["dut1"][-1]),
        "delta_t_first_seconds": float(daily_delta_t[0]),
        "delta_t_last_seconds": float(daily_delta_t[-1]),
        "polar_motion_first_x_arcseconds": float(finals["x_arcseconds"][0]),
        "polar_motion_last_x_arcseconds": float(finals["x_arcseconds"][-1]),
        "polar_motion_first_y_arcseconds": float(finals["y_arcseconds"][0]),
        "polar_motion_last_y_arcseconds": float(finals["y_arcseconds"][-1]),
        "earth_orientation_coverage_start_utc": _utc_midnight_iso(
            _date_from_mjd(utc_mjd[0])
        ),
        "earth_orientation_coverage_end_utc": _utc_midnight_iso(
            _date_from_mjd(utc_mjd[-1])
        ),
        "earth_orientation_reliable_start_utc": _utc_midnight_iso(
            _date_from_mjd(utc_mjd[reliable_indices[0]])
        ),
        "earth_orientation_reliable_end_utc": _utc_midnight_iso(
            _date_from_mjd(utc_mjd[reliable_indices[-1]])
        ),
        "earth_orientation_observed_record_count": int(reliable.sum()),
        "earth_orientation_predicted_record_count": int((~reliable).sum()),
        "earth_orientation_prediction_start_utc": (
            _utc_midnight_iso(_date_from_mjd(utc_mjd[predicted_indices[0]]))
            if len(predicted_indices) else None
        ),
        "earth_orientation_out_of_reliable_coverage_policy": "error",
        "earth_orientation_coverage_semantics": (
            "daily UTC records; endpoints inclusive; reliable means both polar "
            "motion and DUT1 carry the I (observed) flag"
        ),
    }
    return ts, details


def _timescale(mode: str, *, verify: bool, eop_path: str | Path | None):
    """Load an explicitly selected Earth-rotation snapshot."""
    if mode == "builtin_snapshot":
        data_path = Path(importlib.resources.files("skyfield").joinpath("data", "iers.npz"))
        expected = SKYFIELD_IERS_SHA256
        ts = Loader(str(data_path.parent)).timescale(builtin=True)
        polar_motion = "zero (Skyfield default; no polar-motion table installed)"
        source = "skyfield==1.55 bundled iers.npz"
        details = {}
    elif mode in {"iers_snapshot", "iers_file"}:
        if mode == "iers_snapshot":
            data_path = Path(importlib.resources.files("skyfield_data").joinpath(
                "data", "finals2000A.all"))
            expected = FINALS2000A_SHA256
            source = "skyfield-data==7.0.0 finals2000A.all"
        else:
            if eop_path is None:
                raise ValueError("timescale_mode='iers_file' requires eop_path")
            data_path = Path(eop_path)
            expected = None
            source = f"caller-supplied IERS file: {data_path.name}"
        ts, details = _timescale_from_iers_file(data_path)
        polar_motion = "IERS finals2000A x/y installed"
    else:
        raise ValueError("timescale_mode must be builtin_snapshot, iers_snapshot, or iers_file")
    actual = sha256_file(data_path)
    if verify and expected is not None and actual != expected:
        raise RuntimeError(f"Earth-orientation snapshot SHA-256 mismatch: {actual}")
    last_tt = float(ts.delta_t_table[0][-1])
    last_utc = ts.tt_jd(last_tt).utc_datetime().replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - last_utc).total_seconds() / 86400.0
    return ts, {
        "timescale_mode": mode,
        "earth_orientation_source": source,
        "earth_orientation_path": str(data_path.resolve()),
        "earth_orientation_sha256": actual,
        "ut1_delta_t_last_utc": last_utc.isoformat(),
        "earth_orientation_age_days": age_days,
        "earth_orientation_stale": age_days > 180.0,
        "earth_orientation_freshness_limit_days": 180.0,
        "polar_motion": polar_motion,
        "timescale_switching": (
            "explicit only; selected file parsed directly; no automatic network update"
        ),
        **details,
    }


def load_ephemeris(*, verify: bool = True, timescale_mode: str = "builtin_snapshot",
                   eop_path: str | Path | None = None):
    """Load verified DE421 and an explicitly selected Earth-rotation table."""
    path = ephemeris_path()
    if not path.exists():
        raise FileNotFoundError(f"Pinned ephemeris not found at {path}")
    actual = sha256_file(path)
    if verify and actual != DE421_SHA256:
        raise RuntimeError(
            f"DE421 SHA-256 mismatch: expected {DE421_SHA256}, got {actual}. "
            "Refusing an unverified ephemeris."
        )
    eph = load_file(str(path))
    ts, time_provenance = _timescale(timescale_mode, verify=verify, eop_path=eop_path)
    return eph, ts, {
        "ephemeris": EPHEMERIS_NAME,
        "ephemeris_sha256": actual,
        "ephemeris_distribution": "skyfield-data==7.0.0",
        **time_provenance,
    }


def require_reliable_eop_coverage(metadata: dict, start_utc, end_utc) -> None:
    """Reject a requested half-open interval outside observed IERS coverage."""
    start_text = metadata.get("earth_orientation_reliable_start_utc")
    end_text = metadata.get("earth_orientation_reliable_end_utc")
    if start_text is None or end_text is None:
        return

    def as_utc(value):
        if hasattr(value, "to_pydatetime"):
            value = value.to_pydatetime()
        if value.tzinfo is None:
            raise ValueError("EOP coverage check requires timezone-aware dates")
        return value.astimezone(timezone.utc)

    requested_start = as_utc(start_utc)
    requested_end = as_utc(end_utc)
    reliable_start = datetime.fromisoformat(start_text).astimezone(timezone.utc)
    reliable_end_exclusive = (
        datetime.fromisoformat(end_text).astimezone(timezone.utc) + timedelta(days=1)
    )
    if requested_start < reliable_start or requested_end > reliable_end_exclusive:
        raise ValueError(
            "requested interval is outside reliable observed IERS coverage "
            f"[{reliable_start.isoformat()}, {reliable_end_exclusive.isoformat()}); "
            "policy=error and no fallback Earth-orientation source is used"
        )
    metadata["earth_orientation_requested_start_utc"] = requested_start.isoformat()
    metadata["earth_orientation_requested_end_utc"] = requested_end.isoformat()
    metadata["earth_orientation_requested_interval_status"] = "within_reliable_coverage"
