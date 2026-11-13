# Data dictionary

All tabular rows are indexed by `time_utc`, an aware UTC instant. The regular
grid covers `[start_utc, end_utc)`.

| Pattern | Meaning | Unit / convention |
|---|---|---|
| `{body}_distance_m` | simultaneous geometric Earth-center distance | m |
| `{body}_geometric_icrf_{x,y,z}_m` | simultaneous geocentric geometric vector | m, ICRF axes |
| `{body}_geometric_itrs_{x,y,z}_m` | same vector rotated at the sample instant | m, ITRS axes |
| `{body}_altitude_deg` | apparent topocentric, unrefracted altitude | degrees above horizon |
| `{body}_azimuth_deg` | apparent topocentric azimuth | degrees clockwise from north |
| `moon_declination_deg` | apparent topocentric declination | degrees |
| `moon_hour_angle_hours` | local apparent sidereal time minus RA | hours, `[-12,12)`; west positive |
| `moon_phase_angle_deg` | Sun–Moon–Earth angle | degrees; 0 full, 180 new |
| `moon_synodic_phase` | apparent ecliptic longitude difference / 360 | 0 new, ~0.5 full |
| `moon_illuminated_fraction` | geometric illuminated disk fraction | dimensionless `[0,1]` |
| `moon_outdoor_illuminance_lux` | clear-sky horizontal model estimate | lux; zero below horizon |
| `{body}_tidal_itrs_{x,y,z}_m_s2` | exact differential acceleration | m/s², ITRS |
| `{body}_tidal_{east,north,vertical}_m_s2` | local differential acceleration | m/s², ENU; vertical positive up |
| `{body}_tidal_{east,north,vertical}_nm_s2` | same local components | nm/s² |
| `{body}_tidal_magnitude_m_s2` | Euclidean vector norm | m/s², always nonnegative |
| `{body}_tidal_potential_m2_s2` | exact differential potential | m²/s² |
| `{body}_tidal_tensor_{ee..uu}_s-2` | local spatial acceleration Jacobian | s⁻²; row then column ENU |
| `total_*` | Moon plus Sun after frame alignment | same unit as component |
| `*_derivative_m_s3` | finite time derivative | m/s³ |

Metadata records observer coordinates, ellipsoidal height, model name, step,
ephemeris name and SHA-256, library versions, and illuminance assumptions.

## PyGTide validation-only products

These columns are returned only by `compute_pygtide()` and are never merged
into `calculate()` output.

| Column | Meaning | Unit / convention |
|---|---|---|
| `pygtide_rigid_tide_vertical_{down,up}_nm_s2` | `tidalcompo=0`, default unscaled wave groups | nm/s²; sign named in column |
| `pygtide_elastic_body_tide_vertical_{down,up}_nm_s2` | same gravity catalogue with explicit `set_wavegroup([[0,10,factor,0]])` | nm/s²; factor recorded in result |
| `pygtide_pole_tide_vertical_down_nm_s2` | optional pole correction | nm/s², down positive |
| `pygtide_lod_tide_vertical_down_nm_s2` | optional length-of-day correction | nm/s², down positive |
| `pygtide_total_vertical_{down,up}_nm_s2` | configured tide plus enabled corrections | nm/s²; sign named in column |

The former `pygtide_body_tide_vertical_{down,up}_nm_s2` names incorrectly
described the rigid default. They remain temporary, exactly equal deprecated
aliases in rigid results and emit `DeprecationWarning`; elastic results never
expose those ambiguous aliases.
