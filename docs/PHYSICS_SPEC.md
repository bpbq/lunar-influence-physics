# Lunar Influence Physics Engine — Physics Specification

Version: 0.2.0 research preview

## Scope

This package computes astronomical geometry, Newtonian differential tidal
acceleration, and reproducible time aggregates. The primary model is a rigid,
non-deforming WGS84 Earth. Solid-Earth, ocean-loading, pole-tide, and
atmospheric-loading signals are outside the primary model and must remain
separate backend outputs.

## Time scales

Public inputs are timezone-aware UTC instants and intervals are half-open
`[start, end)`. Naive datetimes are rejected. Skyfield converts UTC to TT for
ephemeris evaluation. Earth rotation uses UT1 from the Skyfield timescale/IERS
data when available. UTC contains leap seconds; TT = TAI + 32.184 s. UT1−UTC is
Earth-orientation data and is never assumed to be identically zero silently.
Samples are generated in UTC and retain their exact instants; local civil-day
aggregation converts labels using an IANA timezone and therefore respects DST.

## Reference systems and observer

JPL ephemeris vectors are evaluated in the barycentric celestial reference
system and differenced to obtain geocentric geometric vectors

`R_B = x_B - x_E`,

where `B` is Moon or Sun. For local mechanics these vectors and the observer
position are transformed at the same instant to ITRS, an Earth-fixed Cartesian
frame. ITRS axes are: x through latitude 0°, longitude 0°; y through latitude
0°, longitude +90° east; z through the conventional north pole.

The observer is specified by WGS84 geodetic latitude, east-positive longitude,
and ellipsoidal height in metres. Elevation is not orthometric height; callers
with mean-sea-level heights must apply a geoid correction externally.

The local right-handed ENU basis is

```
east  = (-sin λ, cos λ, 0)
north = (-sin φ cos λ, -sin φ sin λ, cos φ)
up    = ( cos φ cos λ,  cos φ sin λ, sin φ)
```

where φ is geodetic latitude and λ east longitude. Returned local components
are ordered east, north, vertical-up. Positive vertical acceleration is upward.

## Geometric and apparent astronomy

Geometric quantities use simultaneous JPL positions without light-time,
aberration, atmospheric refraction, or deflection. Tidal gravity always uses
these geometric vectors. Observable altitude/azimuth uses Skyfield apparent
topocentric positions, including light-time, aberration, and deflection.
Altitude defaults to unrefracted (`temperature_C=None`, `pressure_mbar=None`).
Any refraction model must be explicitly selected and recorded.

Azimuth is degrees clockwise from true north in `[0, 360)`. Altitude is degrees
above the geometric horizon. Declination is apparent topocentric declination.
Hour angle is `LAST − apparent RA`, wrapped to `[-12 h, 12 h)`; positive means
west of the meridian.

The lunar phase angle `i` is the Sun–Moon–Earth angle: 0 at full Moon and π at
new Moon. Illuminated fraction is `(1 + cos i)/2`. Synodic phase is the wrapped
apparent geocentric ecliptic longitude difference `λ_Moon − λ_Sun`, expressed
in `[0, 1)`, with 0 at new Moon and approximately 0.5 at full Moon.

Rise and set are discrete horizon crossings found with Skyfield almanac
functions. Civil twilight uses a solar center altitude of −6°, nautical −12°,
and astronomical −18°. Event results depend on the selected ephemeris and
Skyfield's event definitions and are separate from the regular sample grid.

## Tidal acceleration

Let `R` be the geocentric ITRS vector from Earth's center to an external body,
and `r` the ITRS vector from Earth's center to the observer. For body parameter
`μ = GM`, the exact differential acceleration is

```
a_tidal = μ [(R-r)/|R-r|³ - R/|R|³].
```

This is acceleration at the observer relative to the geocenter. Moon and Sun
are calculated independently and summed only after both are expressed in ITRS.
Outputs include ITRS vector, ENU components, and Euclidean magnitude, in m/s²
and optionally nm/s² (`1 m/s² = 10⁹ nm/s²`).

The exact differential potential, whose gradient with respect to `r` gives the
specified acceleration, is

`V = μ [1/|R-r| - 1/|R| - (R·r)/|R|³]` in m²/s².

The linearized tidal tensor at observer position is the spatial Jacobian

`T = μ [3 ddᵀ/|d|⁵ - I/|d|³]`, with `d = R-r`,

minus no term because the subtracted geocentric acceleration is independent of
`r`. It has units s⁻². Its leading-order geocentric form is obtained with
`d=R`. The implementation returns the exact local Jacobian and its sum.

Time derivatives are centered finite differences on interior regular samples
and one-sided at endpoints, using actual elapsed SI seconds. Missing or
irregular samples are not interpolated unless an explicit interpolation mode is
requested.

## Aggregation

Vector means are component-wise. `magnitude_of_mean` and `mean_magnitude` are
distinct fields. Scalar summaries are mean, signed mean, min, max,
peak-to-peak, RMS, mean absolute value, time-integrated absolute value,
timestamped extrema, and derivative summaries. If no cadence is supplied, the
shortest timestamp gap is the conservative inferred cadence. Integration uses
trapezoids only between two finite endpoints separated by at most 1.01 nominal
steps. It does not extrapolate to either half-open interval boundary. Coverage
is finite samples divided by nominal sample slots; integrated duration and
excluded gaps are reported. UTC day, IANA local calendar day, arbitrary
half-open interval and sunset-to-sunrise intervals use these rules.

## Lunar illuminance

`illuminated_fraction` is dimensionless geometry and must never be labeled lux.
`outdoor_illuminance_lux` is a separate model output. The MVP uses a documented
empirical clear-sky model based on lunar phase, Earth–Moon distance, altitude,
and an explicit atmospheric extinction coefficient. It is an outdoor
horizontal estimate under simplified atmospheric assumptions. MoonShineR is
an external validation reference, not an interchangeable backend.

## Constants, ephemeris, and reproducibility

The isolated experiment in [DE440S_SENSITIVITY.md](DE440S_SENSITIVITY.md)
uses the official JPL DE440s kernel — the same ephemeridial solution as DE440
for the shorter 1849–2150 time interval — with a separate SHA-256 check.
The candidate does not modify the physical model, fitted constants, IERS
source, or public calculate() default. DE421/DE440s differences are measured
on the exact same grid and must not be interpreted as absolute physical error.

The MVP pins JPL DE421 through `skyfield-data==7.0.0` and file SHA-256
`a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc`, and
records both in each result. Body GM values come from package configuration:
Moon `4.902800118×10¹² m³/s²`, Sun `1.32712440018×10²⁰ m³/s²`.
WGS84 uses semi-major axis 6378137.0 m and flattening 1/298.257223563.

The default time mode is the offline Skyfield 1.55 `iers.npz` snapshot, SHA-256
`c7d7536d898dfa9f8cd43e8044ff51e108cc8289675a13fee9822010a1c4935c`.
It supplies leap seconds, UT1−UTC-derived ΔT, and predictions; polar motion is
zero unless an IERS mode is explicitly selected. `iers_snapshot` uses the
pinned `skyfield-data==7.0.0` `finals2000A.all` snapshot (SHA-256
`d0d9c214fb11f4d1f9418f4075ec4310005f906674a0c4fa3a28232d4d9dd38d`)
for UT1−UTC, ΔT, and x/y polar motion. `iers_file` accepts a caller-supplied
finals2000A-format file under any filename. LIPE parses that exact path directly
and derives UT1−UTC, ΔT, leap seconds, and x/y polar motion from the same
records. It never asks Skyfield's loader to find or download a conventionally
named file. Mode, resolved path, checksum, record count, coverage/freshness,
endpoint DUT1/ΔT, and endpoint polar motion are recorded; LIPE never silently
downloads or switches time standards.

An accepted finals2000A file must contain the complete daily history beginning
at MJD 41684 (1973-01-02). MJD values must be consecutive UTC midnights, the
YY/MM/DD fields must agree with each MJD, and DUT1 discontinuities must occur
only on the published UTC leap-second effective dates. A late fragment is
rejected even if it contains one or more apparent leap jumps, because the
missing earlier jumps make TAI−UTC and therefore ΔT ambiguous. The leap-date
list is versioned in LIPE; a future leap second requires an explicit package
update instead of being accepted silently.

Metadata distinguishes total file coverage from reliable coverage. Reliable
records are the contiguous prefix for which both polar motion and DUT1 carry
the finals2000A `I` (observed) flag; later `P` records are reported separately
as predictions. Coverage endpoints are inclusive daily records. For
`calculate()`, the requested half-open interval must lie within the observed
coverage, whose effective upper boundary is one day after the final reliable
record. The policy is `error`: predicted dates, dates outside the file, and
dates before its first record are rejected, and LIPE does not substitute the
built-in snapshot or another file. Direct `load_ephemeris()` callers receive
the coverage metadata and are responsible for applying an equivalent interval
check if they use the returned Skyfield timescale themselves.

## Accuracy and limitations

DE421 covers 1900–2050 and limits the supported interval. Numerical accuracy is
also limited by Earth-orientation data, ephemeris interpolation, floating-point
precision, finite-difference cadence, and the observer height. The rigid-Earth
acceleration excludes Earth deformation and loading. Unmodified PyGTide 0.9.7 `tidalcompo=0` runs `IRIGID=0` by default.
A factor-one wave group does **not** force all constituent gravity factors to
unity: their relative elastic coefficients survive group normalization. The
former `rigid_gravity()` / `pygtide_rigid_tide_*` nomenclature is deprecated;
the correct output is `default_unit_wavegroup_gravity()` /
`pygtide_unit_wavegroup_tide_*`, and the metadata records
`strict_rigid_newtonian=False`. A separate experimental Fortran build with
`IRIGID=1` is required for strict rigid-vs-rigid verification; the standard
PyGTide API does not expose this switch. Likewise, a uniform amplitude factor
1.16 is only a wavegroup scaling, **not** a verified complete elastic-Earth
rheology model. Neither product can be compared until observable, sign, units,
tide system, components, and corrections are aligned.
Comparisons must report the alignment and remaining theory differences; numeric
agreement is not presented as physical equivalence.
The illuminance model has much larger uncertainty due to aerosols, clouds,
terrain, refraction, and surface orientation.
