import numpy as np

from lunar_physics.illuminance import clear_sky_horizontal_lux


def test_full_zenith_reference_and_horizon():
    values = clear_sky_horizontal_lux(
        np.array([0.0, 0.0]), np.array([384_400_000.0] * 2), np.array([90.0, -1.0])
    )
    assert np.isclose(values[0], 0.25, rtol=1e-3)
    assert values[1] == 0.0


def test_new_moon_is_dimmer_than_full():
    values = clear_sky_horizontal_lux([0, 170], [384_400_000] * 2, [60, 60])
    assert values[1] < values[0] / 1000
