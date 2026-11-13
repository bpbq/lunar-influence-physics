"""Independent Newtonian differential-tide model."""

import numpy as np


def tidal_acceleration(body_itrs_m: np.ndarray, observer_itrs_m: np.ndarray, gm: float) -> np.ndarray:
    """Exact acceleration at observer relative to geocenter, in m/s²."""
    body = np.asarray(body_itrs_m, dtype=float)
    observer = np.asarray(observer_itrs_m, dtype=float)
    delta = body - observer
    return gm * (delta / np.linalg.norm(delta, axis=-1, keepdims=True) ** 3 -
                 body / np.linalg.norm(body, axis=-1, keepdims=True) ** 3)


def tidal_potential(body_itrs_m: np.ndarray, observer_itrs_m: np.ndarray, gm: float) -> np.ndarray:
    """Exact differential potential in m²/s², with gradient equal to acceleration."""
    body = np.asarray(body_itrs_m, dtype=float)
    observer = np.asarray(observer_itrs_m, dtype=float)
    delta = body - observer
    return gm * (1.0 / np.linalg.norm(delta, axis=-1) -
                 1.0 / np.linalg.norm(body, axis=-1) -
                 np.sum(body * observer, axis=-1) / np.linalg.norm(body, axis=-1) ** 3)


def tidal_tensor(body_itrs_m: np.ndarray, observer_itrs_m: np.ndarray, gm: float) -> np.ndarray:
    """Exact Jacobian da/dr in s⁻²."""
    delta = np.asarray(body_itrs_m, float) - np.asarray(observer_itrs_m, float)
    radius = np.linalg.norm(delta, axis=-1)
    outer = delta[..., :, None] * delta[..., None, :]
    eye = np.eye(3)
    return gm * (3.0 * outer / radius[..., None, None] ** 5 -
                 eye / radius[..., None, None] ** 3)
