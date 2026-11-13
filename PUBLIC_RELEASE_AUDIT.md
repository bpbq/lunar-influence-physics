# Public release audit

Audit completed: 2026-11-14. Planned version: `0.2.0`. Planned tag:
`v0.2.0-research-preview`.

## Source and clean history

- Local source snapshot:
  `ed28d65fd5c788769af7621e5914bf1a44147373`.
- The final tree was exported without `.git` into a separate working copy.
- The new repository starts with the root commit
  `Initial public research preview`, followed by ordinary corrective commits;
  it has one branch `main` and no tags.
- The root commit SHA is obtained with `git rev-parse HEAD` and recorded in the
  handoff. A commit cannot embed its own cryptographic SHA in its contents.

## Changes

- Reframed the README as technical documentation for a general-purpose lunar
  and solar physical calculation engine, using the required 15-section layout.
- Retained Newtonian tide equations, constants, WGS84 geometry, sign and unit
  conventions, UTC/TT/UT1 handling, IERS validation, half-open intervals,
  gap-aware aggregation, Python API and CLI.
- Retained JPL Horizons, DE421/DE440s, PyGTide/ETERNA and MoonShineR validation.
- Retained the isolated MPL-2.0 ETERNA `IRIGID=1` patch, build procedure,
  checksums, four 30-day series, metrics, correlations and spectra.
- Removed application-specific positioning and reorganized scientific
  limitations around computational-model boundaries only.
- Removed a specialized interval helper while preserving general arbitrary-
  interval, calendar-day and sunset-to-sunrise aggregation.
- Removed a fictitious release date from `CITATION.cff`; no final release date,
  tag or GitHub Release is asserted.

## Excluded material

- Previous Git history, branches, tags and generated repository-setup notes.
- A skipped external-study placeholder that did not validate an independent
  LIPE physical observable.
- Virtual environments, caches, build products, plots and test XML artifacts.
- Large BSP kernels; official kernels are downloaded only by controlled
  workflows and verified by exact size and SHA-256.
- Local paths, private-resource references and temporary build provenance.

No data or test required to reproduce LIPE's own physical results was removed.

## Tests and packaging

Clean Python 3.12.14 environment:

- `45 passed`, no skips;
- validation metrics regenerated from real reference executions;
- sdist and `lunar_influence_physics-0.2.0-py3-none-any.whl` built successfully;
- wheel installed into a second empty environment;
- installed import, `calculate()`, CLI, CSV, JSON and Parquet smoke checks passed;
- invalid coordinate input remained explicitly rejected.

Test tolerances and physical formulas were not weakened or tuned.

## Licence and provenance review

- LIPE source: MIT.
- Experimental PyGTide/ETERNA source patch: MPL-2.0, with complete licence,
  upstream tag/commit and checksummed bundled inputs.
- JPL Horizons numeric fixtures: request parameters and authority provenance
  retained; no JPL BSP is redistributed.
- MoonShineR numeric fixture: package/source versions, container digest and
  regeneration procedure retained; no MoonShineR source is copied.
- Dependencies remain external and retain their upstream licences.

## Security review

Gitleaks 8.30.1 and the repository's public-snapshot checker scan the complete
new history/tree. The checker rejects credential patterns, local paths,
private-source links and excluded research positioning. Workflows require no
private repository dependency and use read-only contents permission.

## Experiment reproducibility

### DE421 / DE440s

The DE440s BSP matched SHA-256
`c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2`
and exact size 32,726,016 bytes. All eight 30-day comparisons were rerun. The
largest total-vertical absolute difference remained `0.0000204276 nm/s²`.
DE421 remains the default; this is sensitivity, not absolute-accuracy evidence.

### ETERNA `IRIGID=1`

The isolated modified PyGTide 0.9.7 build and four 30-day cases were rerun.
Catalogue 8 RMS remained `0.047322–0.132579 nm/s²`; catalogue 7 remained
`0.019479–0.037849 nm/s²`. One versus four unit groups under true `IRIGID=1`
remained exactly invariant in saved output. No fit was applied.

## Remaining scientific limitations

- The primary gravitational model uses a rigid Earth.
- Elastic deformation, oceanic loading and atmospheric loading are excluded.
- Accuracy depends on ephemeris and Earth-orientation/time-standard inputs.
- Geometric and apparent directions are distinct observables.
- Observer height is WGS84 ellipsoidal height.
- Outdoor illuminance uses simplified atmospheric assumptions.
- Residual differences from harmonic tide models are not fully attributed.
- LIPE is not a complete model of a real gravimeter observation.

## Residual release risks

- External services and compiler/package availability can change.
- The selected validation cases do not span every supported time and location.
- GitHub CI and both manual scientific workflows must be rerun after the owner
  recreates the empty remote repository.
- Final tag, GitHub Release and public visibility require separate approval.

## Verdict

`READY` to recreate the private repository and run independent GitHub checks.
This verdict does not authorize a tag, GitHub Release, or visibility change.
