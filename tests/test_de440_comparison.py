"""Unit tests for the DE421/DE440s experiment (no external kernel required)."""

import numpy as np
import pandas as pd
import pytest

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

# The CLI script is deliberately not part of the installed Python package.
_script = Path(__file__).resolve().parents[1] / "scripts" / "compare_de421_de440s.py"
_spec = spec_from_file_location("lipe_de440s_experiment", _script)
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)

CASES = _module.CASES
DE440S_BYTES = _module.DE440S_BYTES
DE440S_SHA256 = _module.DE440S_SHA256
delta_metrics = _module.delta_metrics
peak_shift_metrics = _module.peak_shift_metrics
physics = _module.physics
verified_de440s = _module.verified_de440s
from lunar_physics import calculate
from lunar_physics.ephemeris import load_ephemeris


def test_de440s_kernel_requires_explicit_verified_bytes(tmp_path):
    with pytest.raises(FileNotFoundError):
        verified_de440s(tmp_path / "missing.bsp")
    fake = tmp_path / "de440s.bsp"
    fake.write_bytes(b"not a real ephemeris")
    with pytest.raises(ValueError, match="size mismatch"):
        verified_de440s(fake)
    assert len(DE440S_SHA256) == 64
    assert DE440S_BYTES == 32726016


def test_delta_metrics_and_peak_matching():
    x = np.array([0.0, 1.0, 0.0, 2.0, 0.0, 1.0, 0.0])
    m = delta_metrics(x, x)
    assert m == {"mean_signed": 0.0, "rms": 0.0, "max_absolute": 0.0,
                 "p95_absolute": 0.0}
    peaks = peak_shift_metrics(x, x, 900)
    assert peaks["matched_peaks"] == 3
    assert peaks["max_absolute_seconds"] == pytest.approx(0)
    assert peaks["median_absolute_seconds"] == pytest.approx(0)


def test_controlled_physics_exactly_reuses_lipe_public_functions():
    start = pd.Timestamp("2024-03-01T00:00:00Z")
    end = start + pd.Timedelta(minutes=45)
    public = calculate(47.6062, -122.3321, 56.0, start, end, 15)
    ephemeris, timescale, _ = load_ephemeris()
    times = timescale.from_datetimes(public.index.to_pydatetime())
    computed = physics(ephemeris, times, 47.6062, -122.3321, 56.0)
    for name in ("moon", "sun"):
        np.testing.assert_allclose(
            computed[f"{name}_vertical_nm_s2"],
            public[f"{name}_tidal_vertical_nm_s2"], rtol=0, atol=1e-10
        )
        np.testing.assert_allclose(
            computed[f"{name}_distance_m"],
            public[f"{name}_distance_m"], rtol=0, atol=1e-6
        )
    np.testing.assert_allclose(
        computed["total_vertical_nm_s2"], public["total_tidal_vertical_nm_s2"],
        rtol=0, atol=1e-10
    )
    assert len(CASES) == 8
