# JPL Horizons fixture provenance

These values are copied verbatim from the Skyfield upstream authority records at
commit `31a6ed7584cd09b6e48e07546a4b5921e1cd5bb4` (MIT license):

- `authorities/moon-phase-angle-fraction-illuminated`: JPL Horizons DE441,
  generated 2022-09-24, geocentric Moon, ten UTC dates spanning new Moon to
  waxing gibbous. Horizons' `S-T-O` includes down-leg aberration and therefore
  differs slightly from LIPE's true geometric phase angle.
- `skyfield/tests/test_against_horizons.py::test_moon_from_boston_geometry`:
  JPL DE430, Boston topocentric Moon vector at 2015-03-02 TDB.
- `authorities/radec-altaz-rates`: JPL Horizons `mar097`, Northern Arizona
  University site, airless apparent Mars azimuth/elevation on 2021-02-03/04 UTC.

The file `horizons_moon_topocentric_altaz_de441.csv` was retrieved directly
from NASA/JPL Horizons API 1.2 on 2026-11-13. It contains 16 verbatim numeric
records: four hourly UTC records at each of Seattle, Leticia, Sydney, and
Tromsø. The sites span northern mid-latitude, equatorial, southern mid-latitude,
and Arctic locations, with dates in January, April, July, and October 2016.

Each request used these parameters (with the site and interval varied):

```text
COMMAND=301
EPHEM_TYPE=OBSERVER
CENTER=coord@399
COORD_TYPE=GEODETIC
SITE_COORD=<east-longitude degrees, latitude degrees, altitude km>
STEP_SIZE=1h
QUANTITIES=4
REF_SYSTEM=ICRF
CAL_FORMAT=CAL
TIME_DIGITS=SECONDS
ANG_FORMAT=DEG
APPARENT=AIRLESS
CSV_FORMAT=YES
EXTRA_PREC=YES
```

Horizons identified both Moon and Earth as DE441, the terrestrial frame as
ITRF93, and its Earth-orientation file as `eop.261112.p270208` (data through
2026-11-12, predictions through 2027-02-07). `QUANTITIES=4` with
`APPARENT=AIRLESS` returns the target centre's topocentric airless apparent
azimuth and elevation. Horizons documents these values as corrected for light
time, gravitational light deflection, stellar aberration, precession, and
nutation, with no atmospheric refraction.

This observable matches LIPE's `observe(...).apparent().altaz()` intent. It is
physically distinct from LIPE's simultaneous geometric Earth-to-Moon ICRF/ITRS
vectors, which contain no light-time or apparent-direction corrections. The
fixture therefore validates the apparent altitude/azimuth path only.

LIPE uses DE421 and its pinned Skyfield Earth-rotation snapshot, while this
fixture uses DE441 and the Horizons EOP file above. Small angular residuals are
expected from ephemeris, Earth-orientation, terrestrial-frame, and correction
implementation differences. No offset or scaling was fitted. The existing
Flagstaff apparent altitude/azimuth fixture still targets Mars (`mar097`) and
is retained as a separate test.
