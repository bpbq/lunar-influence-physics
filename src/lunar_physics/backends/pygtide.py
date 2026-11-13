"""PyGTide adapter. Keep the standard IRIGID=0 transfer distinct from strict rigid gravity."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
import warnings

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PyGTideConfiguration:
    observable: int = 0
    observable_name: str = "tidal gravity"
    unit: str = "nm/s^2"
    sign_convention: str = "PyGTide down-positive; normalized copy up-positive"
    tide_system: str = (
        "PyGTide 0.9.7 default IRIGID=0: unity group gain retains relative "
        "elastic harmonic coefficients; NOT strict rigid Newtonian gravity"
    )
    gravity_model: str = "unit_wavegroup"
    wavegroup_factors: tuple[tuple[float, float, float, float], ...] | None = None
    tidal_potential_catalog: int = 8
    amplitude_truncation_m2_s2: float = 1.0e-10
    pole_tide_factor: float = 0.0
    lod_tide_factor: float = 0.0

    @classmethod
    def default_unit_wavegroup_gravity(cls, **kwargs):
        """Standard PyGTide 0.9.7 IRIGID=0: unit wave group, not strictly rigid."""
        return cls(gravity_model="unit_wavegroup", wavegroup_factors=None, **kwargs)

    @classmethod
    def rigid_gravity(cls, **kwargs):
        """Deprecated naming alias. NOT a true ETERNA IRIGID=1 calculation."""
        return cls.default_unit_wavegroup_gravity(**kwargs)

    @classmethod
    def elastic_body_gravity(cls, *, gravimetric_factor: float = 1.16, **kwargs):
        """Legacy scaled wavegroup mode, NOT a fully validated elastic-Earth model."""
        return cls(
            gravity_model="elastic_body",
            wavegroup_factors=((0.0, 10.0, float(gravimetric_factor), 0.0),),
            tide_system=(
                "PyGTide IRIGID=0 with relative elastic constituent factors and "
                f"explicit uniform group gain {gravimetric_factor:g}; "
                "NOT a validated frequency-dependent physical elastic-Earth response"
            ),
            **kwargs,
        )


def _validate_configuration(configuration):
    if not all((configuration.observable_name, configuration.unit,
                configuration.sign_convention, configuration.tide_system)):
        raise ValueError("all PyGTide physical conventions must be explicit")
    if configuration.gravity_model not in {"unit_wavegroup", "rigid", "elastic_body"}:
        raise ValueError("gravity_model must be unit_wavegroup, rigid (legacy), or elastic_body")
    if configuration.gravity_model in {"unit_wavegroup", "rigid"} and configuration.wavegroup_factors is not None:
        raise ValueError("default unit-wavegroup gravity cannot specify custom wave groups")
    if configuration.gravity_model == "elastic_body" and not configuration.wavegroup_factors:
        raise ValueError("scaled wavegroup configuration requires explicit wavegroup_factors")


def compute_pygtide(*, latitude, longitude, elevation_m, start_utc, duration_hours,
                    step_seconds, configuration: PyGTideConfiguration):
    """Run unmodified PyGTide; report IRIGID=0 and retain deprecated aliases.

    This function DOES NOT produce an ETERNA IRIGID=1 rigid-Earth reference.
    Only the separately built experimental Fortran extension exposes that switch.
    """
    _validate_configuration(configuration)
    if duration_hours <= 0 or float(duration_hours).is_integer() is False:
        raise ValueError("PyGTide duration_hours must be a positive whole number")
    if step_seconds <= 0:
        raise ValueError("step_seconds must be positive")
    try:
        import pygtide
    except ImportError as exc:
        raise RuntimeError("install the 'validation' extra to use PyGTide") from exc

    start = pd.Timestamp(start_utc)
    if start.tzinfo is None:
        raise ValueError("start_utc must be timezone-aware")
    start = start.tz_convert("UTC").to_pydatetime().replace(tzinfo=None)

    tide = pygtide.pygtide(msg=False)
    if configuration.wavegroup_factors is not None:
        tide.set_wavegroup(np.asarray(configuration.wavegroup_factors, dtype=float))
    controls = {
        "tidalcompo": configuration.observable,
        "tidalpoten": configuration.tidal_potential_catalog,
        "amtruncate": configuration.amplitude_truncation_m2_s2,
        "poltidecor": configuration.pole_tide_factor,
        "lodtidecor": configuration.lod_tide_factor,
    }
    tide.predict(
        latitude, longitude, elevation_m, start, duration_hours, step_seconds,
        **controls,
    )
    raw = tide.results(digits=12).copy().rename(columns={"UTC": "time_utc"})
    effective_model = (
        "unit_wavegroup" if configuration.gravity_model in {"unit_wavegroup", "rigid"}
        else configuration.gravity_model
    )
    deprecated_columns = {}
    if configuration.observable == 0:
        total_down = raw["Signal [nm/s**2]"]
        pole_down = raw["Pole tide [nm/s**2]"]
        lod_down = raw["LOD tide [nm/s**2]"]
        gravity_down = total_down - pole_down - lod_down
        stem = "unit_wavegroup_tide" if effective_model == "unit_wavegroup" else "elastic_body_tide"
        normalized = pd.DataFrame({
            "time_utc": pd.to_datetime(raw["time_utc"], utc=True),
            f"pygtide_{stem}_vertical_down_nm_s2": gravity_down,
            "pygtide_pole_tide_vertical_down_nm_s2": pole_down,
            "pygtide_lod_tide_vertical_down_nm_s2": lod_down,
            "pygtide_total_vertical_down_nm_s2": total_down,
            f"pygtide_{stem}_vertical_up_nm_s2": -gravity_down,
            "pygtide_total_vertical_up_nm_s2": -total_down,
        })
        if effective_model == "unit_wavegroup":
            deprecated_columns = {
                "pygtide_body_tide_vertical_down_nm_s2": "pygtide_unit_wavegroup_tide_vertical_down_nm_s2",
                "pygtide_body_tide_vertical_up_nm_s2": "pygtide_unit_wavegroup_tide_vertical_up_nm_s2",
                "pygtide_rigid_tide_vertical_down_nm_s2": "pygtide_unit_wavegroup_tide_vertical_down_nm_s2",
                "pygtide_rigid_tide_vertical_up_nm_s2": "pygtide_unit_wavegroup_tide_vertical_up_nm_s2",
            }
            for old, new in deprecated_columns.items():
                normalized[old] = normalized[new]
            warnings.warn(
                "PyGTide IRIGID=0 retains relative elastic constituent factors. "
                "Use pygtide_unit_wavegroup_tide_*; old rigid/body aliases are deprecated.",
                DeprecationWarning, stacklevel=2,
            )
    else:
        normalized = raw
    return {
        "backend": f"pygtide-{effective_model.replace('_', '-')}-gravity",
        "configuration": configuration,
        "controls": controls,
        "wavegroup_factors": configuration.wavegroup_factors,
        "pygtide_version": importlib.metadata.version("pygtide"),
        "fortran_version": tide.fortran_version,
        "data": normalized,
        "raw_data": raw,
        "deprecated_columns": deprecated_columns,
        "eterna_irigid": 0,
        "strict_rigid_newtonian": False,
        "model_separation": (
            f"PyGTide {effective_model} output is not an exact LIPE Newtonian rigid reference. "
            "The unmodified Fortran has IRIGID=0 and retains relative elastic constituent "
            "factors. PyGTide gravity is down-positive; LIPE vertical is up-positive."
        ),
        "comparison_status": "SEPARATE VALIDATION BACKEND; NOT STRICT IRIGID=1",
    }
