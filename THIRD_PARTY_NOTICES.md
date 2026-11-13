# Third-party notices and reference-data provenance

LIPE source code is MIT licensed. Dependencies are installed separately and
retain their own licences.

## JPL and Horizons

DE421 is obtained from the `skyfield-data` package; DE440s is downloaded only by
the optional sensitivity workflow from NASA NAIF and verified by SHA-256. No BSP
kernel is stored in this repository. Fixed Horizons numeric outputs identify the
request parameters, retrieval date and JPL solution in
`tests/validation/data/HORIZONS_PROVENANCE.md`. These factual US Government
astronomical records are included for scientific verification with attribution.

## MoonShineR

The repository stores generated numeric output, not MoonShineR source code.
Package versions, source commits, container digest and regeneration commands are
in `tests/validation/data/MOONSHINER_PROVENANCE.md`. MoonShineR and its R
dependencies retain their respective licences.

## PyGTide and ETERNA PREDICT

PyGTide 0.9.7 and its ETERNA Fortran source are Mozilla Public License 2.0.
The optional file
`experiments/pygtide-irigid/pygtide_irigid_v0_9_7.patch` is a source-form
modification of that MPL-covered file and is distributed under MPL-2.0. The full
licence is in `licenses/MPL-2.0.txt`. The patch records upstream tag `v0.9.7`
and commit `e2587918bbeba27bd3464da1002396393856cd03`; it is not part of the LIPE
runtime package and is not presented as an upstream PyGTide feature.
