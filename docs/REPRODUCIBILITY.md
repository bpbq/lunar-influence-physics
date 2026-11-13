# Reproducibility

## Standard LIPE environment

Use Python 3.12 and the exact dependency versions in
`requirements/validation.lock`. Install LIPE itself without dependency
resolution so the lock remains authoritative:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements/validation.lock
python -m pip install --no-deps -e .
pytest
python scripts/validation_metrics.py
```

At runtime, metadata records package versions, model choices, ephemeris path and
SHA-256, and time-data provenance. DE421 and the default Earth-orientation data
work offline. A caller-selected IERS table is never silently replaced.

## Installed-wheel smoke test

```bash
python -m build
python3.12 -m venv /tmp/lipe-wheel-test
/tmp/lipe-wheel-test/bin/pip install dist/lunar_influence_physics-0.2.0-py3-none-any.whl
/tmp/lipe-wheel-test/bin/python scripts/smoke_installed_wheel.py
```

The smoke test imports the installed distribution outside the source tree,
runs `calculate()`, then writes CSV, JSON and (when `pyarrow` is installed)
Parquet with metadata.

## Optional external comparisons

- DE421/DE440s: follow `docs/DE440S_SENSITIVITY.md`. The DE440s BSP is downloaded
  from NAIF, checked for exact size and SHA-256, and never committed.
- ETERNA `IRIGID=1`: follow
  `experiments/pygtide-irigid/README.md`. This compiles an isolated modified
  PyGTide 0.9.7 and does not alter the installed standard package.
- MoonShineR fixture: run `scripts/reproduce_moonshiner_fixture.sh`; its container
  image is pinned by digest.

Network-dependent comparisons are separate from standard offline tests. A
failed or unavailable external execution must be reported as `NOT REVERIFIED`,
not inferred from archived output.
