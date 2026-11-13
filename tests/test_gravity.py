import numpy as np

from lunar_physics.gravity import tidal_acceleration, tidal_potential, tidal_tensor


def test_far_field_radial_limit():
    radius, observer_radius, gm = 4.0e8, 6.0e6, 4.9e12
    body = np.array([radius, 0.0, 0.0])
    observer = np.array([observer_radius, 0.0, 0.0])
    exact = tidal_acceleration(body, observer, gm)
    leading = 2.0 * gm * observer_radius / radius ** 3
    assert exact[0] > 0
    assert np.isclose(exact[0], leading, rtol=0.03)
    assert np.allclose(exact[1:], 0.0)


def test_potential_gradient_and_tensor():
    body = np.array([3.84e8, 1.0e7, -2.0e7])
    observer = np.array([4.0e6, -3.0e6, 2.0e6])
    gm, step = 4.9028e12, 100.0
    acceleration = tidal_acceleration(body, observer, gm)
    gradient = []
    for axis in range(3):
        delta = np.zeros(3); delta[axis] = step
        gradient.append((tidal_potential(body, observer + delta, gm) -
                         tidal_potential(body, observer - delta, gm)) / (2 * step))
    assert np.allclose(gradient, acceleration, rtol=5e-8, atol=1e-15)
    tensor = tidal_tensor(body, observer, gm)
    assert np.allclose(tensor, tensor.T)
    assert abs(np.trace(tensor)) < 1e-20
