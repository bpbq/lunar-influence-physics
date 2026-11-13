import numpy as np

from lunar_physics.frames import enu_basis, wgs84_position


def test_enu_is_right_handed_orthonormal():
    basis = enu_basis(47.6, -122.3)
    assert np.allclose(basis @ basis.T, np.eye(3), atol=1e-15)
    assert np.allclose(np.cross(basis[0], basis[1]), basis[2])


def test_wgs84_equator_axes():
    assert np.allclose(wgs84_position(0, 0, 0), [6_378_137, 0, 0])
    assert np.allclose(wgs84_position(0, 90, 0), [0, 6_378_137, 0], atol=1e-8)


def test_enu_cardinal_directions_at_equator_prime_meridian():
    basis = enu_basis(0, 0)
    assert np.allclose(basis[0], [0, 1, 0])
    assert np.allclose(basis[1], [0, 0, 1])
    assert np.allclose(basis[2], [1, 0, 0])
