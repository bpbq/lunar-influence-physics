# v0.2.0-research-preview release notes

Status: prepared, not yet released or tagged.

This first public research preview provides the documented LIPE 0.2.0 Python
package, CLI, pinned environment, scientific tests and independently
reproducible validation material.

Verified functions include geometric astronomy, local apparent Moon/Sun
directions, exact Newtonian differential tide, ENU components, potential,
tensor, derivatives, gap-aware aggregation, structured exports and provenance.

Known limitations include rigid-Earth physics, no oceanic or atmospheric
loading, approximate outdoor illuminance, and small incompletely attributed
differences from ETERNA `IRIGID=1`. This is a research-preview computational
engine, not a complete model of gravimeter observations.

Reproduction instructions are in `docs/REPRODUCIBILITY.md`; detailed numerical
status is in `VALIDATION_REPORT.md`.
