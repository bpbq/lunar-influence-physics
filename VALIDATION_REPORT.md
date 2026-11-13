# Validation report — v0.2.0 research preview

Run date: 2026-11-13 UTC. Machine-readable results are in
`validation/metrics.json`; fixtures and provenance are under
`tests/validation/data`. CI produces the complete test log per run rather than
committing a machine-specific XML artifact.

## Correctness fixes

- PyGTide 0.9.7 now receives the component as `tidalcompo=`. The adapter passes
  `tidalpoten`, `amtruncate`, `poltidecor`, and `lodtidecor` explicitly.
- A deeper Fortran audit of PyGTide 0.9.7 (source commit
  `e2587918bbeba27bd3464da1002396393856cd03`) found that standard
  `tidalcompo=0` **does not set `IRIGID=1`**. Even a default amplitude-one
  wave group retains relative latitude/frequency-dependent elastic `DBODY`
  factors. Consequently the former `rigid_gravity()` name and
  `pygtide_rigid_tide_*` output columns were scientifically misleading.
  Use `default_unit_wavegroup_gravity()` and
  `pygtide_unit_wavegroup_tide_*` instead; older output column names
  remain deprecated, warning-emitting aliases. The result advertises
  `eterna_irigid=0` and `strict_rigid_newtonian=False`.
  A factor-1.16 wave group is only a scaling, **not a fully validated
  elastic-Earth rheological response**. Pole, LOD, sign and total columns
  remain separate.
- Aggregation now infers the conservative cadence from the shortest timestamp
  gap when no step is supplied. A trapezoid is accepted only between two finite
  values no more than 1.01 steps apart. Coverage is finite sample slots divided
  by nominal slots in the half-open interval. Integration never extrapolates to
  interval boundaries; integrated duration and rejected gap count are returned.
- The public calculation interval is checked against the documented DE421 range
  `[1900-01-01, 2051-01-01)`.
- A single-timestamp daily group no longer aborts aggregation when cadence is
  unavailable; it returns `insufficient_timestamps_for_step`, null coverage and
  integral, and no invented cadence.

## JPL Horizons — PARTIAL

Real Horizons authority records were obtained from Skyfield upstream commit
`31a6ed7584cd09b6e48e07546a4b5921e1cd5bb4`. LIPE uses DE421 while the fixtures
use DE430/DE441 or the target-specific `mar097` solution.

| Quantity | Samples | Maximum absolute error | RMS error |
|---|---:|---:|---:|
| Moon phase angle | 10 | 0.005562° | 0.005236° |
| Illuminated fraction | 10 | 0.00006223 | 0.00004577 |
| Boston topocentric Moon vector components | 3 | 8.97 m | 6.53 m |
| Flagstaff airless apparent azimuth | 2 | 0.0000621° | 0.0000454° |
| Flagstaff airless apparent altitude | 2 | 0.0000439° | 0.0000424° |
| Moon topocentric airless apparent azimuth | 16 | 0.0002502° | 0.0001246° |
| Moon topocentric airless apparent altitude | 16 | 0.00008381° | 0.00004137° |

The phase fixture's Horizons `S-T-O` includes down-leg aberration; LIPE's phase
angle is true geometric. Those quantities are expected to differ by a few
thousandths of a degree.

The Moon altitude/azimuth fixture was retrieved directly from Horizons API 1.2
on 2026-11-13: four hourly samples each for Seattle, Leticia, Sydney, and Tromsø
on dates in four seasons. Horizons used DE441, ITRF93, and
`eop.261112.p270208`; LIPE used DE421 and its pinned Skyfield time snapshot.
Both sides compute topocentric airless apparent directions. Horizons explicitly
includes light time, gravitational light deflection, stellar aberration,
precession, and nutation. This is a **VERIFIED** external comparison of LIPE's
apparent altitude/azimuth path, with the measured DE421/DE441 and EOP difference
left intact.

Boston's DE430 Moon record is instead a geometric topocentric ICRF vector. The
LIPE geometric ICRF/ITRS vectors are simultaneous positions without apparent
light-path corrections, so the new apparent fixture does not validate those
geometric fields. The Mars `mar097` test remains separate.

## PyGTide 0.9.7 default IRIGID=0 — VERIFIED execution, NOT a strict rigid reference

Four real 30-day calculations use 15-minute cadence in 2016, within PyGTide's
bundled leap-second and pole tables. Coordinates are WGS84 and heights are
ellipsoidal. `tidalcompo=0`, Kudryavtsev 2004 catalogue, `amtruncate=1e-10`,
`poltidecor=0`, and `lodtidecor=0` were used. PyGTide down-positive gravity was
negated before comparison with LIPE up-positive vertical acceleration.

| Case | Samples | Max abs. | RMS | Mean bias (LIPE−PyGTide) | Correlation |
|---|---:|---:|---:|---:|---:|
| Seattle, winter | 2880 | 26.446 nm/s² | 9.876 nm/s² | 6.613 nm/s² | 0.9999557 |
| Leticia, spring | 2880 | 5.129 nm/s² | 2.336 nm/s² | 1.954 nm/s² | 0.9999980 |
| Sydney, winter | 2880 | 11.800 nm/s² | 5.933 nm/s² | 1.297 nm/s² | 0.9999597 |
| Tromsø, autumn | 2880 | 8.215 nm/s² | 4.798 nm/s² | 0.016 nm/s² | 0.9999524 |

These data were originally labelled "rigid-vs-rigid", but that label is
incorrect: the standard PyGTide IRIGID=0 default retains relative elastic
constituent coefficients. The original multi-nm/s² residual was reproduced
and largely explained by comparison against a separately patched *true*
ETERNA IRIGID=1 build, giving 0.019–0.133 nm/s² RMS depending on site and
catalogue. The complete diagnostic, patch, build instructions, raw series and
spectra are included in this repository:
[experimental IRIGID investigation](docs/PYGTIDE_IRIGID_INVESTIGATION.md).
That experiment is not included in standard CI and is not a physical
calibration of LIPE. LIPE evaluates exact Newtonian differential acceleration from DE421,
whereas PyGTide/ETERNA evaluates the Kudryavtsev 2004 harmonic catalogue with
different astronomical arguments, catalogue truncation, Earth/observer
geometry, and time tables. Pole and LOD were disabled. No coefficient, constant,
or scale factor was fitted.

After removing the mean, the three largest 30-day FFT bins show mostly diurnal,
semidiurnal and higher-frequency structure: Seattle 1.933/0.933/2.000 cpd
(7.835/4.452/3.849 nm/s²), Leticia 2.900/1.000/0.967 cpd
(1.199/1.073/0.560), Sydney 1.000/0.933/2.900 cpd
(7.997/1.024/0.669), and Tromsø 1.000/0.933/0.967 cpd
(6.560/0.917/0.789). The site/season-dependent bias and spectrum establish that
the discrepancy is not a single scale error; attribution among catalogue,
geometry, and time arguments remains open. Elastic/body output with explicit
factor 1.16 is configuration-tested but is not used as the rigid reference.

## MoonShineR 1.2.0 — PARTIAL

MoonShineR was run in a pinned R 4.5.2 container for Seattle, Leticia, Sydney,
and Tromsø, two days each at one-hour cadence, with sea-level elevation and
`darksky_value=0`. LIPE was then evaluated from MoonShineR's own phase, distance,
and altitude columns so the comparison isolates the light model.

| Case | Above-horizon samples | Maximum absolute error | RMS error |
|---|---:|---:|---:|
| Seattle, winter | 30 | 0.011481 lux | 0.005687 lux |
| Leticia, spring | 26 | 0.0000315 lux | 0.0000137 lux |
| Sydney, winter | 28 | 0.017354 lux | 0.008657 lux |
| Tromsø, autumn | 19 | 0.000000497 lux | 0.000000205 lux |
| All cases | 103 | 0.017354 lux | 0.005458 lux |

MoonShineR includes waxing/waning asymmetry, an opposition surge, a 0.863 field
calibration, and a different atmospheric-extinction curve. LIPE's clear-sky
screening model omits those terms. Its outdoor illuminance therefore has only
approximate accuracy and is not a substitute for measured outdoor or indoor
exposure. The scientific model was not changed to reduce these differences.

An additional end-to-end benchmark uses LIPE's DE421/Skyfield geometry instead
of feeding MoonShineR geometry into LIPE. Across 103 above-horizon samples, max
/ RMS errors were 2.214° / 1.112° altitude, 1.613° / 0.972° phase angle,
6990.8 / 3696.2 km distance, and 0.016282 / 0.006260 lux. MoonShineR uses
suncalc geometry, so this verifies execution and quantifies combined astronomy
plus light-model differences; it is not JPL-grade geometry validation. The
light-only test remains separate.

## Earth orientation and time provenance — VERIFIED implementation

The default offline mode pins Skyfield 1.55 `iers.npz` by SHA-256 and records
its ΔT/UT1 coverage, freshness, and zero-polar-motion convention. A separate
fixed `skyfield-data==7.0.0` `finals2000A.all` mode installs x/y polar motion and
records its checksum. Updating requires explicit `iers_file` selection and a
caller-supplied file; there is no automatic download or silent mode change.
The custom-file validator requires the complete daily finals2000A history from
MJD 41684, verifies calendar fields and the official DUT1 leap-jump dates, and
rejects gaps and late fragments. Tests include the pinned real table, two
distinct synthetic complete tables, a conventional-name decoy, a late fragment
with one leap jump, a calendar gap, a false leap date, and a date/MJD mismatch.
Metadata reports total, observed, and predicted coverage. `calculate()` uses a
strict error policy outside the contiguous observed (`I`) interval, including
dates covered only by predicted (`P`) rows. Freshness and coverage never trigger
an automatic standards substitution.

## Test coverage and reproducibility

The suite additionally covers NaN gaps, irregular timestamps, half-open boundary
semantics, spring and autumn DST days, UTC normalization, DE421 limits, polar
latitudes, ENU handedness/cardinal axes, analytical gravity limits, potential
gradient, tensor symmetry/trace, and derivatives on irregular timestamps.

Run:

```bash
python -m pip install -r requirements/validation.lock
python -m pip install --no-deps -e .
pytest
python scripts/validation_metrics.py
```

MoonShineR regeneration uses `scripts/reproduce_moonshiner_fixture.sh` and a
container image pinned by digest. Python dependencies are exact in
`requirements/validation.lock`; CI installs that file.

## Open questions

- Multi-site Moon apparent altitude/azimuth is **VERIFIED** against direct JPL
  Horizons DE441 fixtures; geometric vectors retain their separate DE430 check.
- PyGTide's post-2017 leap-second warning and pole/LOD table ending 2024-11-23
  prevent treating later runs as independently current without data updates.
- Attribution of rigid LIPE−PyGTide residual spectral lines remains **PARTIAL**;
  the measured errors are reported without assigning them to Earth deformation.

## JPL DE440s versus DE421 — CONTROLLED sensitivity, NOT absolute accuracy

The isolated SHA-verified DE440s comparison (same DE440 solution over a shorter
span, **not** the ETERNA tidal catalogue #8) was executed on four sites,
30 days each in 2016 and 2024: eight windows, 2,880 points per window.
The exact same LIPE Newtonian model, GM constants, WGS84 geodetic position,
15-minute grid and IERS time scale were used. No physical constant or
calibration parameter was fitted. The maximum absolute difference in
the **total vertical tide** was **0.0000204276 nm/s²**, and the
maximum Moon-distance difference was **0.470441 m**. On these intervals
DE421 vs DE440s is not a material explanation for the earlier LIPE–PyGTide
inter-model mismatch.

Reproduce with [scripts/compare_de421_de440s.py](scripts/compare_de421_de440s.py)
and see [docs/DE440S_SENSITIVITY.md](docs/DE440S_SENSITIVITY.md) for case-by-case
results and kernel source/checksum. The official JPL DE440s BSP is verified by
SHA-256 in the separate manually launchable GitHub Actions workflow; its
artifact contains all signed differences and peak-time metrics. This is model
sensitivity only, not an independent comparison with gravimeter measurements.
