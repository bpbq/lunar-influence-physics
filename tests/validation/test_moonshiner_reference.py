from pathlib import Path

import numpy as np
import pandas as pd

from lunar_physics import calculate
from lunar_physics.illuminance import clear_sky_horizontal_lux

DATA = Path(__file__).with_name("data")


def test_real_moonshiner_fixture_quantifies_model_difference():
    reference = pd.read_csv(DATA / "moonshiner_1_2_0.csv").dropna(subset=["Z_moon"])
    actual = clear_sky_horizontal_lux(
        reference["phase_angle"].to_numpy(),
        reference["distance"].to_numpy() * 1000.0,
        90.0 - reference["Z_moon"].to_numpy(),
    )
    error_lux = actual - reference["moon_final_lux"].to_numpy()
    assert set(reference["scenario"]) == {
        "seattle_winter", "leticia_spring", "sydney_winter", "tromso_autumn"
    }
    # Regression envelope for two documented, non-equivalent clear-sky models.
    assert np.max(np.abs(error_lux)) < 0.018
    assert np.sqrt(np.mean(error_lux ** 2)) < 0.0055


def test_end_to_end_moon_geometry_and_illuminance_against_moonshiner():
    """Keep astronomy differences in this test; the test above isolates light."""
    reference = pd.read_csv(DATA / "moonshiner_1_2_0.csv", parse_dates=["time_utc"])
    errors = {name: [] for name in ("altitude_deg", "phase_angle_deg", "distance_km", "lux")}
    for _, case in reference.groupby("scenario"):
        actual = calculate(
            case["latitude_deg"].iloc[0], case["longitude_deg"].iloc[0], 0.0,
            case["time_utc"].min(), case["time_utc"].max() + pd.Timedelta(hours=1), 60,
        ).reindex(pd.DatetimeIndex(case["time_utc"]))
        visible = case["Z_moon"].notna().to_numpy()
        # MoonShineR/suncalc uses a signed phase angle; LIPE stores [0, 180].
        reference_phase = np.abs(case["phase_angle"].to_numpy())
        comparisons = {
            "altitude_deg": actual["moon_altitude_deg"].to_numpy()
                - (90.0 - case["Z_moon"].to_numpy()),
            "phase_angle_deg": actual["moon_phase_angle_deg"].to_numpy() - reference_phase,
            "distance_km": actual["moon_distance_m"].to_numpy() / 1000.0
                - case["distance"].to_numpy(),
            "lux": actual["moon_outdoor_illuminance_lux"].to_numpy()
                - case["moon_final_lux"].to_numpy(),
        }
        for name, values in comparisons.items():
            errors[name].extend(values[visible])

    # Broad regression envelopes: suncalc and DE421/Skyfield are independent,
    # non-equivalent astronomy implementations, and the light models differ.
    assert np.max(np.abs(errors["altitude_deg"])) < 2.3
    assert np.max(np.abs(errors["phase_angle_deg"])) < 2.0
    assert np.max(np.abs(errors["distance_km"])) < 7100.0
    assert np.max(np.abs(errors["lux"])) < 0.017
