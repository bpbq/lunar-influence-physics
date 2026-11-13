# DE421 vs DE440s — controlled ephemeris sensitivity (2026-11-13)

## Question and distinction

**DE440s is a JPL planetary/lunar ephemeris, NOT ETERNA tidal-potential catalogue 7 or 8.**
The compact `de440s.bsp` file is the **same DE440 solution** over a shorter
date range (1849–2150), so no replacement of tide theory is implied.

We ask: if LIPE uses the same Newtonian differential-tide physics, same GM
constants, same WGS84 observer, same UT1/TT timescale and same 15-minute samples,
how much does switching from JPL DE421 to DE440s change the calculated forcing?

## Execution and provenance

- Tested at four sites (Seattle, Leticia, Sydney, Tromsø), one 30-day
  period in 2016 and one 30-day period in 2024: **eight 30-day cases**.
- The exact study inputs, physical calls, local-peak interpolation and
  independent SHA-256 verification are in
  [scripts/compare_de421_de440s.py](../scripts/compare_de421_de440s.py).
- DE421: pinned `skyfield-data==7.0.0` checksum
  `a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc`.
- DE440s: original
  `https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp`;
  **32,726,016 bytes**, SHA-256
  `c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2`.
  SHA and size must match; no silent download/fallback in the Python script.
- The manually launchable GitHub Actions workflow downloads the kernel, checks
  SHA and size, computes all comparisons and uploads the full JSON artifact.
  The table below is also stored as machine-readable output; a release workflow
  must independently reproduce it before being labelled verified in CI.
- Both paths share the **same** Skyfield time scale from `load_ephemeris()`.
  The rest of the LIPE model, including `geometric_body_vectors_itrs()`,
  `tidal_acceleration()`, `wgs84_position()` and `enu_basis()`, is unchanged.
- No rescaling, fitted phase, lag, bias correction or additional corrections.

## Numerical results — reverified during public release preparation

The table was reproduced on 2026-11-13 from the SHA-verified kernel downloaded
through JPL's official `ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440s.bsp`
endpoint. Machine-readable output is committed as
[`validation/de440s_comparison.json`](../validation/de440s_comparison.json).

Differences are DE440s minus DE421. Each series has 2,880 samples (15-minute
cadence × 30 days). All changes are much smaller than the residual against
ETERNA's strict `IRIGID=1` reference.

| Site, year | Lunar tide RMS Δ (nm/s²) | Total vertical tide maximum absolute Δ (nm/s²) | Lunar distance max absolute Δ (m) |
|---|---:|---:|---:|
| Seattle 2016 | 0.0000031055 | 0.0000073395 | 0.32793 |
| Leticia 2016 | 0.0000062245 | 0.0000137598 | 0.35416 |
| Sydney 2016 | 0.0000043798 | 0.0000096655 | 0.31072 |
| Tromsø 2016 | 0.0000014592 | 0.0000038333 | 0.36599 |
| Seattle 2024 | 0.0000058683 | 0.0000156572 | 0.47044 |
| Leticia 2024 | 0.0000096336 | 0.0000204276 | 0.39354 |
| Sydney 2024 | 0.0000075015 | 0.0000171101 | 0.45096 |
| Tromsø 2024 | 0.0000033300 | 0.0000093448 | 0.43456 |

The machine-readable JSON also provides solar components, the sum,
vector magnitude, mean/p95/RMS/max differences, and parabolically interpolated
local maximum timing shifts in seconds. Across the matched local peaks,
the largest estimated shift was **0.0003414 s** for lunar vertical-tide maxima
and **0.0003737 s** for total vertical-tide maxima (both at Tromsø in their
respective 2024 and 2016 cases). **These submillisecond differences are
algorithmic estimates from parabolic interpolation on a 15-minute grid,
not a demonstrated submillisecond physical timing accuracy.**

### Interpretation

- On these specific 2016/2024 dates, **DE421 vs DE440s is not a material source
  of the earlier LIPE/PyGTide mismatch** (formerly several nm/s² before a
  strict `IRIGID=1` comparison).
- DE421 was not demonstrably inaccurate for this observable and date range.
  Agreement between ephemerides does **not establish which is closer to nature**.
- This is a **sensitivity test**, not a laboratory validation of real gravimeter
  observations or an error budget covering every year.
- The old ETERNA potential catalogues 7 (HW95) and 8 (Kudryavtsev 2004) should
  not be confused with the planetary ephemerides DE421 and DE440. Changing the
  ephemeris is not changing the harmonic tide catalogue.

## Reproduce

The comparison deliberately does not replace the production DE421 default.

```bash
python -m pip install -r requirements/validation.lock
python -m pip install --no-deps -e .
mkdir -p .cache/de440
curl -fL --retry 3 -o .cache/de440/de440s.bsp \
  https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp
echo 'c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2  .cache/de440/de440s.bsp' | sha256sum -c -
python scripts/compare_de421_de440s.py \
  --de440s-path .cache/de440/de440s.bsp \
  --output artifacts/de440s_comparison.json
```

The large BSP must remain out of Git; only code, hashes and results are versioned.
The comparison does not establish that replacing DE421 improves absolute
accuracy; DE421 remains the public default.
