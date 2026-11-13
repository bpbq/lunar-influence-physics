import numpy as np
import pandas as pd
import pytest

pygtide = pytest.importorskip("pygtide")

from lunar_physics.backends.pygtide import PyGTideConfiguration, compute_pygtide
from lunar_physics import calculate


def test_real_pygtide_gravity_call_uses_explicit_controls_and_sign():
    config = PyGTideConfiguration.default_unit_wavegroup_gravity(
        pole_tide_factor=0.0,
        lod_tide_factor=0.0,
    )
    with pytest.warns(DeprecationWarning):
        result = compute_pygtide(
            latitude=47.6062, longitude=-122.3321, elevation_m=56.0,
            start_utc="2016-01-01T00:00:00Z", duration_hours=1,
            step_seconds=1800, configuration=config,
        )
    assert result["controls"]["tidalcompo"] == 0
    assert result["controls"]["poltidecor"] == 0.0
    assert result["controls"]["lodtidecor"] == 0.0
    data = result["data"]
    assert len(data) == 3
    assert np.allclose(
        data["pygtide_unit_wavegroup_tide_vertical_up_nm_s2"],
        -data["pygtide_unit_wavegroup_tide_vertical_down_nm_s2"],
    )
    assert np.allclose(data["pygtide_pole_tide_vertical_down_nm_s2"], 0.0)
    assert np.allclose(data["pygtide_lod_tide_vertical_down_nm_s2"], 0.0)


def test_pole_and_lod_are_separate_from_wavegroup_tide():
    config = PyGTideConfiguration.default_unit_wavegroup_gravity(
        pole_tide_factor=1.16, lod_tide_factor=1.16,
    )
    with pytest.warns(DeprecationWarning):
        result = compute_pygtide(
            latitude=47.6062, longitude=-122.3321, elevation_m=56,
            start_utc="2016-01-01T00:00:00Z", duration_hours=1,
            step_seconds=1800, configuration=config,
        )
    data = result["data"]
    reconstructed = (
        data["pygtide_unit_wavegroup_tide_vertical_down_nm_s2"]
        + data["pygtide_pole_tide_vertical_down_nm_s2"]
        + data["pygtide_lod_tide_vertical_down_nm_s2"]
    )
    assert np.allclose(reconstructed, data["pygtide_total_vertical_down_nm_s2"])
    assert np.any(np.abs(data["pygtide_pole_tide_vertical_down_nm_s2"]) > 0)


@pytest.mark.parametrize(
    "latitude,longitude,elevation_m,start_utc",
    [
        (47.6062, -122.3321, 56.0, "2016-01-22T00:00:00Z"),
        (-4.21528, -69.94056, 0.0, "2016-04-06T00:00:00Z"),
        (-33.8688, 151.2093, 0.0, "2016-07-18T00:00:00Z"),
        (69.6492, 18.9553, 0.0, "2016-10-29T00:00:00Z"),
    ],
)
def test_lipe_vs_default_wavegroup_tide_quantified(
    latitude, longitude, elevation_m, start_utc
):
    start = pd.Timestamp(start_utc)
    rigid = calculate(
        latitude, longitude, elevation_m, start, start + pd.Timedelta(days=1), 15
    )
    config = PyGTideConfiguration.default_unit_wavegroup_gravity(
        pole_tide_factor=0.0, lod_tide_factor=0.0,
    )
    with pytest.warns(DeprecationWarning):
        comparison = compute_pygtide(
            latitude=latitude, longitude=longitude, elevation_m=elevation_m,
            start_utc=start, duration_hours=24, step_seconds=900,
            configuration=config,
        )["data"].set_index("time_utc")
    pygtide_up = comparison["pygtide_unit_wavegroup_tide_vertical_up_nm_s2"].reindex(rigid.index)
    error = rigid["total_tidal_vertical_nm_s2"] - pygtide_up
    # These are distinct theories/catalogues. The bound catches sign, unit,
    # timestamp, and correction mistakes; it is not a fitted equivalence claim.
    assert error.abs().max() < 20.0
    assert rigid["total_tidal_vertical_nm_s2"].corr(pygtide_up) > 0.9998


def test_elastic_body_tide_has_explicit_wavegroup_and_distinct_columns():
    config = PyGTideConfiguration.elastic_body_gravity(gravimetric_factor=1.16)
    result = compute_pygtide(
        latitude=47.6062, longitude=-122.3321, elevation_m=56.0,
        start_utc="2016-01-01T00:00:00Z", duration_hours=1,
        step_seconds=1800, configuration=config,
    )
    assert result["wavegroup_factors"] == ((0.0, 10.0, 1.16, 0.0),)
    assert result["backend"] == "pygtide-elastic-body-gravity"
    assert "pygtide_elastic_body_tide_vertical_up_nm_s2" in result["data"]
    assert "pygtide_body_tide_vertical_up_nm_s2" not in result["data"]


def test_legacy_rigid_alias_is_equal_and_declared_deprecated():
    with pytest.warns(DeprecationWarning):
        result = compute_pygtide(
            latitude=0.0, longitude=0.0, elevation_m=0.0,
            start_utc="2016-01-01T00:00:00Z", duration_hours=1,
            step_seconds=1800, configuration=PyGTideConfiguration.default_unit_wavegroup_gravity(),
        )
    data = result["data"]
    assert np.array_equal(data["pygtide_body_tide_vertical_up_nm_s2"],
                          data["pygtide_unit_wavegroup_tide_vertical_up_nm_s2"])
    assert result["deprecated_columns"]["pygtide_body_tide_vertical_up_nm_s2"] == \
        "pygtide_unit_wavegroup_tide_vertical_up_nm_s2"
    assert result["eterna_irigid"] == 0
    assert result["strict_rigid_newtonian"] is False
    assert result["backend"] == "pygtide-unit-wavegroup-gravity"
    assert np.array_equal(data["pygtide_rigid_tide_vertical_up_nm_s2"],
                          data["pygtide_unit_wavegroup_tide_vertical_up_nm_s2"])
    assert "NOT strict rigid Newtonian" in result["configuration"].tide_system
