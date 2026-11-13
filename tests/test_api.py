import pandas as pd
import pytest
import numpy as np

from lunar_physics.api import _derivative, _utc, calculate


def test_naive_time_rejected():
    with pytest.raises(ValueError):
        _utc("2026-01-01")


def test_aware_time_normalized():
    assert _utc("2026-01-01T03:00:00+03:00") == pd.Timestamp("2026-01-01T00:00:00Z")


def test_calculate_half_open_grid_and_component_sum():
    data = calculate(47.6062, -122.3321, 56, "2026-01-01T00:00:00Z",
                     "2026-01-01T01:00:00Z", 15)
    assert len(data) == 4
    assert data.index[-1] == pd.Timestamp("2026-01-01T00:45:00Z")
    assert np.allclose(
        data["total_tidal_vertical_m_s2"],
        data["moon_tidal_vertical_m_s2"] + data["sun_tidal_vertical_m_s2"],
    )
    assert data.attrs["metadata"]["ephemeris_sha256"].startswith("a20a7139")


def test_de421_declared_boundaries():
    for start, end in (
        ("1900-01-01T00:00Z", "1900-01-01T00:30Z"),
        ("2050-12-31T23:00Z", "2051-01-01T00:00Z"),
    ):
        assert not calculate(0, 0, 0, start, end, 15).empty
    with pytest.raises(ValueError, match="DE421 supported"):
        calculate(0, 0, 0, "1899-12-31T23:00Z", "1900-01-01T00:00Z", 15)
    with pytest.raises(ValueError, match="DE421 supported"):
        calculate(0, 0, 0, "2050-12-31T23:00Z", "2051-01-01T00:15Z", 15)


def test_polar_latitude_and_derivative_frequency():
    data = calculate(89.0, 20.0, 10.0, "2026-06-20T00:00Z", "2026-06-20T02:00Z", 15)
    assert np.isfinite(data["moon_altitude_deg"]).all()
    idx = pd.to_datetime([
        "2026-01-01T00:00:00Z", "2026-01-01T00:10:00Z", "2026-01-01T00:30:00Z"
    ])
    seconds = np.array([stamp.timestamp() for stamp in idx])
    assert np.allclose(_derivative(3.0 * seconds + 2.0, idx), 3.0)
