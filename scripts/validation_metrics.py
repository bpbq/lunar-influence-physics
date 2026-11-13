"""Run the external-reference comparisons and emit machine-readable metrics."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from skyfield.api import wgs84

from lunar_physics import calculate
from lunar_physics.astronomy import local_observables, lunar_phase
from lunar_physics.backends.pygtide import PyGTideConfiguration, compute_pygtide
from lunar_physics.ephemeris import load_ephemeris
from lunar_physics.illuminance import clear_sky_horizontal_lux

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "validation" / "data"
AU_M = 149_597_870_700.0
CASES = [
    ("seattle_winter", 47.6062, -122.3321, 56.0, "2016-01-22T00:00:00Z"),
    ("leticia_spring", -4.21528, -69.94056, 0.0, "2016-04-06T00:00:00Z"),
    ("sydney_winter", -33.8688, 151.2093, 0.0, "2016-07-18T00:00:00Z"),
    ("tromso_autumn", 69.6492, 18.9553, 0.0, "2016-10-29T00:00:00Z"),
]


def error_metrics(error) -> dict:
    values = np.asarray(error, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        raise ValueError("no finite errors to summarize")
    return {
        "n": int(values.size),
        "max_absolute": float(np.max(np.abs(values))),
        "rms": float(np.sqrt(np.mean(values ** 2))),
        "mean_signed": float(np.mean(values)),
    }


def horizons_metrics() -> dict:
    eph, ts, _ = load_ephemeris()
    phase_ref = pd.read_csv(DATA / "horizons_moon_phase_de441.csv")
    instants = pd.to_datetime(phase_ref.time_utc, utc=True)
    phase = lunar_phase(eph, ts.from_datetimes(instants.dt.to_pydatetime()))
    results = {
        "phase_angle_deg": error_metrics(phase["phase_angle_deg"] - phase_ref.phase_angle_deg),
        "illuminated_fraction": error_metrics(
            phase["illuminated_fraction"] - phase_ref.illuminated_fraction
        ),
    }

    topo = pd.read_csv(DATA / "horizons_topocentric.csv")
    boston = topo.iloc[0]
    observer = eph["earth"] + wgs84.latlon(
        boston.latitude_deg, boston.longitude_deg, elevation_m=boston.elevation_m
    )
    vector = (eph["moon"] - observer).at(ts.tdb(2015, 3, 2)).xyz.au
    expected = boston[["reference_x_au", "reference_y_au", "reference_z_au"]].to_numpy(float)
    results["boston_moon_vector_m"] = error_metrics((vector - expected) * AU_M)

    flagstaff = topo.iloc[1:]
    flagstaff_times = pd.to_datetime(flagstaff.time_value, utc=True)
    observed = local_observables(
        eph, ts.from_datetimes(flagstaff_times.dt.to_pydatetime()),
        flagstaff.iloc[0].latitude_deg, flagstaff.iloc[0].longitude_deg,
        flagstaff.iloc[0].elevation_m, "mars",
    )
    results["flagstaff_azimuth_deg"] = error_metrics(
        observed["azimuth_deg"] - flagstaff.reference_azimuth_deg
    )
    results["flagstaff_altitude_deg"] = error_metrics(
        observed["altitude_deg"] - flagstaff.reference_altitude_deg
    )
    moon_topo = pd.read_csv(DATA / "horizons_moon_topocentric_altaz_de441.csv")
    moon_az_errors = []
    moon_alt_errors = []
    for _, site in moon_topo.groupby("scenario", sort=False):
        site_times = pd.to_datetime(site.time_utc, utc=True)
        observed = local_observables(
            eph, ts.from_datetimes(site_times.dt.to_pydatetime()),
            site.iloc[0].latitude_deg, site.iloc[0].longitude_deg,
            site.iloc[0].elevation_m, "moon",
        )
        moon_az_errors.extend(
            (observed["azimuth_deg"] - site.reference_azimuth_deg.to_numpy()
             + 180.0) % 360.0 - 180.0
        )
        moon_alt_errors.extend(
            observed["altitude_deg"] - site.reference_altitude_deg.to_numpy()
        )
    results["moon_topocentric_airless_apparent_azimuth_deg"] = error_metrics(
        moon_az_errors
    )
    results["moon_topocentric_airless_apparent_altitude_deg"] = error_metrics(
        moon_alt_errors
    )
    return results


def moonshiner_metrics() -> dict:
    reference = pd.read_csv(DATA / "moonshiner_1_2_0.csv").dropna(subset=["Z_moon"])
    actual = clear_sky_horizontal_lux(
        reference.phase_angle, reference.distance * 1000.0, 90.0 - reference.Z_moon
    )
    reference = reference.assign(error_lux=actual - reference.moon_final_lux)
    result = {name: error_metrics(group.error_lux) for name, group in reference.groupby("scenario")}
    result["all_cases"] = error_metrics(reference.error_lux)
    end_to_end = {key: [] for key in ("altitude_deg", "phase_angle_deg", "distance_km", "lux")}
    full = pd.read_csv(DATA / "moonshiner_1_2_0.csv", parse_dates=["time_utc"])
    for _, case in full.groupby("scenario"):
        actual = calculate(
            case.latitude_deg.iloc[0], case.longitude_deg.iloc[0], 0.0,
            case.time_utc.min(), case.time_utc.max() + pd.Timedelta(hours=1), 60,
        ).reindex(pd.DatetimeIndex(case.time_utc))
        mask = case.Z_moon.notna().to_numpy()
        values = {
            "altitude_deg": actual.moon_altitude_deg.to_numpy() - (90.0 - case.Z_moon.to_numpy()),
            "phase_angle_deg": actual.moon_phase_angle_deg.to_numpy() - np.abs(case.phase_angle.to_numpy()),
            "distance_km": actual.moon_distance_m.to_numpy() / 1000.0 - case.distance.to_numpy(),
            "lux": actual.moon_outdoor_illuminance_lux.to_numpy() - case.moon_final_lux.to_numpy(),
        }
        for key, value in values.items():
            end_to_end[key].extend(value[mask])
    result["end_to_end_all_cases"] = {
        key: error_metrics(value) for key, value in end_to_end.items()
    }
    return result


def pygtide_metrics() -> dict:
    config = PyGTideConfiguration.default_unit_wavegroup_gravity(
        pole_tide_factor=0.0, lod_tide_factor=0.0,
    )
    output = {}
    for name, latitude, longitude, elevation_m, start_utc in CASES:
        start = pd.Timestamp(start_utc)
        rigid = calculate(
            latitude, longitude, elevation_m, start, start + pd.Timedelta(days=30), 15
        )
        reference = compute_pygtide(
            latitude=latitude, longitude=longitude, elevation_m=elevation_m,
            start_utc=start, duration_hours=30 * 24, step_seconds=900,
            configuration=config,
        )["data"].set_index("time_utc")
        rigid_up = rigid.total_tidal_vertical_nm_s2
        reference_up = reference.pygtide_unit_wavegroup_tide_vertical_up_nm_s2.reindex(rigid.index)
        residual = rigid_up - reference_up
        metrics = error_metrics(residual)
        metrics["correlation"] = float(rigid_up.corr(reference_up))
        centered = residual.to_numpy() - residual.mean()
        frequencies = np.fft.rfftfreq(len(centered), d=900.0) * 86400.0
        amplitude = 2.0 * np.abs(np.fft.rfft(centered)) / len(centered)
        order = np.argsort(amplitude[1:])[-3:][::-1] + 1
        metrics["dominant_residual_frequencies_cycles_per_day"] = [
            {"frequency": float(frequencies[i]), "amplitude_nm_s2": float(amplitude[i])}
            for i in order
        ]
        output[name] = metrics
    return output


def main():
    result = {
        "generated_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "horizons": horizons_metrics(),
        "pygtide_0_9_7": pygtide_metrics(),
        "moonshiner_1_2_0": moonshiner_metrics(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
