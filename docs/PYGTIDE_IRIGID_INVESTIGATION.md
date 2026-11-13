# PyGTide/ETERNA `IRIGID` investigation

Status: re-executed in the public release preparation environment on 2026-11-13;
still not an external validation of either model. PyGTide 0.9.7 standard
execution and the modified `IRIGID=1` execution are distinct throughout.

## Source trace

In unmodified ETERNA PREDICT v3.4 shipped by PyGTide 0.9.7, `PREDIN` assigns
`IRIGID=0`; the Python argument array does not expose it. `ETPOTS` obtains
latitude/frequency-dependent elastic factors from `ETGCON`/`ETLOVE` and stores
them as `DBODY(IW)`. For each group, the strongest wave supplies
`DBOD(IG)=DBODY(IW)`. PREDICT then applies
`DFAC=DG0(IG)/DBOD(IG)` and scales every wave by `DFAC*DBODY(IW)`.

Therefore an amplitude-one wavegroup under standard `IRIGID=0` retains relative
elastic factors `DBODY(IW)/DBOD(IG)` and is sensitive to group boundaries. It
is not a strict Newtonian unity transfer. With `IRIGID=1`, PREDICT explicitly
sets `DBODY=1`, so a unit group gives `DBOD=DFAC=1`.

## Archived 30-day results

All errors are LIPE minus PyGTide after converting PyGTide down-positive gravity
to LIPE geodetic-up-positive acceleration. Units are nm/s². Pole/LOD corrections
are disabled. There was no fitted scale, offset, phase, lag or coefficient.

| Site | Standard IRIGID=0 cat 8 RMS | 4 unit bands IRIGID=0 RMS | true IRIGID=1 cat 8 RMS | true IRIGID=1 cat 7 RMS |
|---|---:|---:|---:|---:|
| Seattle | 9.875895 | 3.714562 | 0.072413 | 0.026005 |
| Leticia | 2.336432 | 0.679658 | 0.132579 | 0.024296 |
| Sydney | 5.932517 | 3.452462 | 0.092698 | 0.019479 |
| Tromsø | 4.797655 | 2.596584 | 0.047322 | 0.037849 |

For true IRIGID=1 catalogue 8, one group and four unit groups were identical to
machine output precision (maximum absolute difference `0.0 nm/s²`). Complete
bias, centered RMS, maxima, correlations and spectra are in
`validation/pygtide_residuals_v2`.

Catalogue 7 reducing this particular residual does not establish it as a more
accurate universal theory. Remaining differences can include harmonic catalogue
truncation and arguments, GRS80/WGS84 geometry, time tables and DE421 positions.
The archived geometry test found the ETERNA-like ellipsoid effect below
0.000080 nm/s² RMS; geocentric rather than geodetic vertical was much worse.
The remaining residual is not completely attributed.

## Conclusion

Standard PyGTide 0.9.7 `IRIGID=0` is correctly described by LIPE as
`default_unit_wavegroup_gravity()`, not a strict Newtonian rigid reference. The
isolated modified build supports the `DBODY/DBOD/DFAC` diagnosis, but it is not
standard PyGTide and does not validate LIPE against measurements.
