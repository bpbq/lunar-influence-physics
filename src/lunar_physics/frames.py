"""WGS84 and local-frame transformations."""

import numpy as np

from .constants import WGS84_A_M, WGS84_F


def wgs84_position(lat_deg: float, lon_deg: float, elevation_m: float) -> np.ndarray:
    """Return geocentric ITRS position in metres."""
    lat, lon = np.deg2rad([lat_deg, lon_deg])
    e2 = WGS84_F * (2.0 - WGS84_F)
    n = WGS84_A_M / np.sqrt(1.0 - e2 * np.sin(lat) ** 2)
    return np.array([
        (n + elevation_m) * np.cos(lat) * np.cos(lon),
        (n + elevation_m) * np.cos(lat) * np.sin(lon),
        (n * (1.0 - e2) + elevation_m) * np.sin(lat),
    ])


def enu_basis(lat_deg: float, lon_deg: float) -> np.ndarray:
    """Rows map ITRS vectors to [east, north, up]."""
    lat, lon = np.deg2rad([lat_deg, lon_deg])
    return np.array([
        [-np.sin(lon), np.cos(lon), 0.0],
        [-np.sin(lat) * np.cos(lon), -np.sin(lat) * np.sin(lon), np.cos(lat)],
        [np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)],
    ])
