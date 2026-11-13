# Changelog

## 0.2.0 — Research preview (unreleased)

- Publish the independently versioned LIPE package and scientific specification.
- Provide Newtonian lunar/solar differential tide, astronomy, time provenance,
  interval aggregation, approximate illuminance, CLI and structured exports.
- Correct PyGTide terminology: standard PyGTide 0.9.7 uses `IRIGID=0` and is
  exposed as `default_unit_wavegroup_gravity()`; misleading legacy names remain
  deprecated aliases.
- Add fixed JPL Horizons and MoonShineR fixtures, controlled DE421/DE440s
  sensitivity results, and the isolated ETERNA `IRIGID=1` diagnostic appendix.
- Validate explicit IERS files for leap-second history, calendar continuity,
  DUT1 jumps, observed coverage and provenance.

Known limitations are documented in `README.md` and `VALIDATION_REPORT.md`.
