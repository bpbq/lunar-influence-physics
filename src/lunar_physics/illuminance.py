"""Explicit outdoor lunar-illuminance estimate."""

import numpy as np


def clear_sky_horizontal_lux(
    phase_angle_deg,
    moon_distance_m,
    altitude_deg,
    *,
    extinction_mag_per_airmass: float = 0.172,
):
    """Estimate outdoor horizontal illuminance under a clear sky.

    Uses the Krisciunas–Schaefer lunar magnitude phase relation, inverse-square
    distance scaling, Kasten–Young optical airmass, and a 0.25 lux calibration
    for mean-distance full Moon at zenith. Values are zero below the horizon.
    This is a screening model, not an indoor-exposure estimate.
    """
    alpha = np.abs(np.asarray(phase_angle_deg, float))
    altitude = np.asarray(altitude_deg, float)
    distance = np.asarray(moon_distance_m, float)
    phase_delta_mag = 0.026 * alpha + 4.0e-9 * alpha ** 4
    phase_ratio = 10.0 ** (-0.4 * phase_delta_mag)
    mean_distance = 384_400_000.0
    distance_ratio = (mean_distance / distance) ** 2
    z = 90.0 - np.clip(altitude, -5.0, 90.0)
    airmass = 1.0 / (np.cos(np.deg2rad(z)) + 0.50572 * (96.07995 - z) ** -1.6364)
    transmission = 10.0 ** (-0.4 * extinction_mag_per_airmass * (airmass - 1.0))
    horizontal = np.maximum(np.sin(np.deg2rad(altitude)), 0.0)
    return np.where(altitude > 0.0, 0.25 * phase_ratio * distance_ratio * transmission * horizontal, 0.0)
