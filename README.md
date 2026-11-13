# Lunar Influence Physics Engine

## Overview

Lunar Influence Physics Engine (LIPE) is an open-source Python engine for
reproducible calculations of lunar and solar astronomy, Newtonian differential
tidal acceleration, and related physical observables.

Version 0.2.0 is a research preview with explicit definitions, units,
assumptions, reference-data provenance, and reproducible validation.

## Features

- geometric Earth–Moon and Earth–Sun vectors and distances;
- apparent local altitude and azimuth, lunar declination and hour angle;
- phase angle, synodic phase, illuminated fraction, rise/set and twilight;
- exact Newtonian differential tidal acceleration for Moon and Sun separately;
- ITRS vectors, local east/north/geodetic-up components and magnitude;
- differential potential, spatial tidal tensor and time derivatives;
- approximate clear-sky outdoor lunar illuminance;
- gap-aware interval and calendar-day summaries;
- CSV, JSON and Parquet exports with model metadata.

## Physical model

For an external body with geocentric ITRS vector `R`, observer vector `r`, and
gravitational parameter `GM`, LIPE evaluates

```text
a_tidal = GM [(R-r)/|R-r|³ - R/|R|³].
```

Moon and Sun are evaluated independently and then summed. WGS84 defines the
observer position; local vertical is geodetic up. SI units are authoritative,
with acceleration also represented in nm/s². Time grids are half-open
`[start, end)`. Full definitions are in
[docs/PHYSICS_SPEC.md](docs/PHYSICS_SPEC.md).

## Installation

Python 3.12 is required.

```bash
git clone https://github.com/bpbq/lunar-influence-physics.git
cd lunar-influence-physics
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements/validation.lock
python -m pip install --no-deps -e .
```

## Quick start

```python
from lunar_physics import calculate

result = calculate(
    47.6062, -122.3321, 56.0,
    "2026-01-01T00:00:00Z",
    "2026-01-02T00:00:00Z",
    15,
)
print(result[["moon_altitude_deg", "total_tidal_vertical_nm_s2"]].head())
```

## Python API

The primary interface is:

```python
calculate(lat, lon, elevation_m, start_utc, end_utc, step_minutes=15)
```

Inputs must use timezone-aware UTC timestamps. `elevation_m` is WGS84
ellipsoidal height. Optional arguments select the explicit time-data mode and
caller-managed IERS file. The returned `pandas.DataFrame` carries provenance
and configuration in `frame.attrs["metadata"]`.

## Command-line interface

```bash
lunar-physics compute \
  --lat 47.6062 --lon -122.3321 --elevation-m 56 \
  --start 2026-01-01T00:00:00Z --end 2026-01-02T00:00:00Z \
  --step-minutes 15 --output seattle.parquet
```

The output extension selects CSV, JSON, Parquet, or PQ.

## Outputs and units

Outputs include geometric vectors in metres, angles in degrees or hours,
accelerations in m/s² and nm/s², potential in m²/s², tidal-tensor components
in s⁻², derivatives in m/s³, illuminated fraction as a dimensionless value,
and outdoor illuminance in lux. CSV and Parquet receive a sibling metadata
JSON; JSON contains `metadata` and `records`. See
[DATA_DICTIONARY.md](DATA_DICTIONARY.md) for the complete schema.

## Ephemerides and time standards

DE421 from pinned `skyfield-data==7.0.0` is the default and its BSP SHA-256 is
verified at runtime. DE440s is used only in a controlled sensitivity experiment.
UTC input, TT ephemeris time and UT1 Earth rotation remain distinct. Default
Earth-orientation data are offline and checksummed. Explicit IERS files are
validated for calendar continuity, leap-second history, DUT1 jumps, reliable
coverage and provenance; LIPE does not silently substitute another source.

## Validation

Validation includes analytical limits, coordinate and unit invariants, DST and
time-zone cases, ephemeris boundaries, fixed JPL Horizons records, real standard
PyGTide 0.9.7 execution, an isolated ETERNA `IRIGID=1` experiment, DE421/DE440s
sensitivity, and MoonShineR-generated illuminance fixtures. Distinct theories
remain explicitly distinct and no scale, offset, lag, phase, or coefficient is
fitted for agreement. See [VALIDATION_REPORT.md](VALIDATION_REPORT.md).

## Reproducibility

```bash
pytest
python scripts/validation_metrics.py
python -m build
```

Dependency versions are pinned, input data are checksummed, and machine-readable
validation results are included. Detailed clean-environment, wheel, DE440s and
experimental ETERNA procedures are in
[docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).

## Scientific limitations

- The primary gravitational calculation uses a rigid Earth.
- Elastic Earth deformation is not part of the primary Newtonian signal.
- Oceanic and atmospheric loading are not included.
- Accuracy depends on the selected ephemeris and time standards.
- Geometric vectors and apparent astronomical directions are different
  observables and must not be interchanged.
- Observer height is relative to the WGS84 ellipsoid, not a geoid or mean sea
  level surface.
- Lunar illuminance is approximate and depends on simplified atmospheric
  assumptions.
- Residual differences from harmonic tide models are not fully attributed.
- LIPE is not a complete model of a real gravimeter measurement.

Agreement with another computational model is not presented as accuracy
relative to nature.

## Contributing

Physics changes must document equations, frames, time scales, signs, units,
assumptions, provenance and independent tests. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## Citation

Use the versioned metadata in [CITATION.cff](CITATION.cff).

## License

LIPE is licensed under the [MIT License](LICENSE). The separately identified
PyGTide/ETERNA experimental patch remains MPL-2.0; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
