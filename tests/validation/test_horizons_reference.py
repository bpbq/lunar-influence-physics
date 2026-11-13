from pathlib import Path

import numpy as np
import pandas as pd
from skyfield.api import wgs84

from lunar_physics.astronomy import local_observables, lunar_phase
from lunar_physics.ephemeris import load_ephemeris

DATA = Path(__file__).with_name("data")
AU_M = 149_597_870_700.0


def test_real_horizons_lunar_phase_fixture():
    reference = pd.read_csv(DATA / "horizons_moon_phase_de441.csv")
    instants = pd.to_datetime(reference["time_utc"], utc=True)
    eph, ts, _ = load_ephemeris()
    actual = lunar_phase(eph, ts.from_datetimes(instants.dt.to_pydatetime()))
    angle_error = actual["phase_angle_deg"] - reference["phase_angle_deg"].to_numpy()
    fraction_error = actual["illuminated_fraction"] - reference["illuminated_fraction"].to_numpy()
    assert np.max(np.abs(angle_error)) < 0.006
    assert np.sqrt(np.mean(angle_error ** 2)) < 0.0055
    assert np.max(np.abs(fraction_error)) < 7e-5
    assert np.sqrt(np.mean(fraction_error ** 2)) < 5e-5


def test_real_horizons_boston_moon_topocentric_vector():
    reference = pd.read_csv(DATA / "horizons_topocentric.csv").iloc[0]
    eph, ts, _ = load_ephemeris()
    observer = eph["earth"] + wgs84.latlon(
        reference.latitude_deg, reference.longitude_deg, elevation_m=reference.elevation_m
    )
    actual = (eph["moon"] - observer).at(ts.tdb(2015, 3, 2)).xyz.au
    expected = reference[["reference_x_au", "reference_y_au", "reference_z_au"]].to_numpy(float)
    error_m = (actual - expected) * AU_M
    assert np.linalg.norm(error_m) < 12.0


def test_real_horizons_flagstaff_airless_altaz():
    reference = pd.read_csv(DATA / "horizons_topocentric.csv").iloc[1:]
    eph, ts, _ = load_ephemeris()
    instants = pd.to_datetime(reference["time_value"], utc=True)
    actual = local_observables(
        eph, ts.from_datetimes(instants.dt.to_pydatetime()),
        reference.iloc[0].latitude_deg, reference.iloc[0].longitude_deg,
        reference.iloc[0].elevation_m, "mars",
    )
    az_error = actual["azimuth_deg"] - reference["reference_azimuth_deg"].to_numpy()
    alt_error = actual["altitude_deg"] - reference["reference_altitude_deg"].to_numpy()
    assert np.max(np.abs(az_error)) < 7e-5
    assert np.max(np.abs(alt_error)) < 5e-5


def test_real_horizons_moon_airless_apparent_altaz_multi_site():
    """Compare like-for-like apparent directions; this is not geometric ITRS."""
    reference = pd.read_csv(DATA / "horizons_moon_topocentric_altaz_de441.csv")
    assert len(reference) == 16
    assert set(reference["scenario"]) == {
        "seattle_winter", "leticia_spring", "sydney_winter", "tromso_autumn",
    }
    assert set(reference["reference_ephemeris"]) == {"DE441"}
    assert set(reference["reference_observable"]) == {
        "airless_apparent_topocentric"
    }
    eph, ts, _ = load_ephemeris()
    az_errors = []
    alt_errors = []
    for _, site in reference.groupby("scenario", sort=False):
        instants = pd.to_datetime(site["time_utc"], utc=True)
        actual = local_observables(
            eph, ts.from_datetimes(instants.dt.to_pydatetime()),
            site.iloc[0].latitude_deg, site.iloc[0].longitude_deg,
            site.iloc[0].elevation_m, "moon",
        )
        # Circular difference avoids a false 360-degree error at north.
        az_error = (
            actual["azimuth_deg"] - site["reference_azimuth_deg"].to_numpy()
            + 180.0
        ) % 360.0 - 180.0
        az_errors.extend(az_error)
        alt_errors.extend(
            actual["altitude_deg"] - site["reference_altitude_deg"].to_numpy()
        )

    az_errors = np.asarray(az_errors)
    alt_errors = np.asarray(alt_errors)
    # Horizons uses DE441 plus its current EOP; LIPE uses DE421 plus its pinned
    # time snapshot. These bounds quantify that model difference without fitting.
    assert np.max(np.abs(az_errors)) < 3e-4
    assert np.sqrt(np.mean(az_errors ** 2)) < 1.3e-4
    assert np.max(np.abs(alt_errors)) < 1e-4
    assert np.sqrt(np.mean(alt_errors ** 2)) < 5e-5
