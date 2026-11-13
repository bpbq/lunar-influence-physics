#!/usr/bin/env python3
"""Generate the frozen IRIGID residual diagnostic artifacts (no fitting)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pygtide
from pygtide import etpred

from lunar_physics import calculate
from lunar_physics.constants import GM_MOON, GM_SUN
from lunar_physics.frames import enu_basis, wgs84_position
from lunar_physics.gravity import tidal_acceleration

CASES = (
    ("seattle", 47.6062, -122.3321, 56.0, "2016-01-22T00:00:00Z"),
    ("leticia", -4.21528, -69.94056, 0.0, "2016-04-06T00:00:00Z"),
    ("sydney", -33.8688, 151.2093, 0.0, "2016-07-18T00:00:00Z"),
    ("tromso", 69.6492, 18.9553, 0.0, "2016-10-29T00:00:00Z"),
)
GROUPS = np.array([[0, .5, 1, 0], [.5, 1.5, 1, 0],
                   [1.5, 2.5, 1, 0], [2.5, 10, 1, 0]], dtype=float)
N = 30 * 96


def run_pygtide(lat, lon, elev, start, *, irigid=0, groups=None, catalogue=8):
    etpred.setirigid(irigid)
    tide = pygtide.pygtide(msg=False)
    if groups is not None:
        tide.set_wavegroup(groups)
    tide.predict(lat, lon, elev, pd.Timestamp(start).to_pydatetime().replace(tzinfo=None),
                 30 * 24, 900, tidalcompo=0, tidalpoten=catalogue,
                 amtruncate=1e-10, poltidecor=0.0, lodtidecor=0.0)
    assert int(round(float(etpred.controlmod.irigid))) == irigid
    # ETERNA gravity is positive down; LIPE up is positive.
    result = -tide.results(digits=12)["Signal [nm/s**2]"].to_numpy(float)[:N]
    etpred.setirigid(0)
    return result


def metrics(x, y):
    r = np.asarray(x) - np.asarray(y)
    return {"bias_nm_s2": float(r.mean()), "rms_nm_s2": float(np.sqrt(np.mean(r*r))),
            "centered_rms_nm_s2": float(r.std()), "max_abs_nm_s2": float(np.abs(r).max()),
            "correlation": float(np.corrcoef(x, y)[0, 1])}


def grs80_like_position(lat_deg, lon_deg, height):
    lat, lon = np.deg2rad([lat_deg, lon_deg])
    a, e2 = 6378136.3, 6.69439795140e-3
    n = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
    return np.array([(n + height)*np.cos(lat)*np.cos(lon),
                     (n + height)*np.cos(lat)*np.sin(lon),
                     (n*(1-e2) + height)*np.sin(lat)])


def spectrum(residual):
    r = np.asarray(residual) - np.mean(residual)
    return np.fft.rfftfreq(len(r), d=900)*86400, 2*np.abs(np.fft.rfft(r))/len(r)


def main():
    if not hasattr(etpred, "setirigid"):
        raise SystemExit("NOT VERIFIED: import an explicitly patched PyGTide 0.9.7 build")
    root = Path(__file__).resolve().parents[2]
    out = root / "validation" / "pygtide_residuals_v2"
    out.mkdir(parents=True, exist_ok=True)
    report = {"provenance": {"pygtide_version": pygtide.__version__,
              "pygtide_source_commit": "e2587918bbeba27bd3464da1002396393856cd03",
              "experimental_patch": "experiments/pygtide-irigid/pygtide_irigid_v0_9_7.patch",
              "pygtide_module": "isolated experimental build; local path omitted",
              "samples": N, "step_seconds": 900, "duration_days": 30,
              "pygtide_tidal_component": 0, "pygtide_amtruncate": 1e-10,
              "pole_tide_correction": 0.0, "lod_tide_correction": 0.0,
              "vertical_sign": "LIPE geodetic up; PyGTide gravity negated from down to up",
              "fitting": "none; no scale, offset, phase, or lag was fitted"}, "sites": {}}
    spectra = []
    for site, lat, lon, elev, start in CASES:
        begin = pd.Timestamp(start); end = begin + pd.Timedelta(days=30)
        frame = calculate(lat, lon, elev, begin, end, 15)
        lipe = frame["total_tidal_vertical_nm_s2"].to_numpy()
        itrs = frame[[f"total_tidal_itrs_{a}_m_s2" for a in "xyz"]].to_numpy()
        radial = itrs @ (wgs84_position(lat, lon, elev)/np.linalg.norm(wgs84_position(lat, lon, elev))) * 1e9
        grs_r = grs80_like_position(lat, lon, elev)
        up = enu_basis(lat, lon)[2]
        grs = np.zeros(N)
        for body, gm in (("moon", GM_MOON), ("sun", GM_SUN)):
            b = frame[[f"{body}_geometric_itrs_{a}_m" for a in "xyz"]].to_numpy()
            grs += tidal_acceleration(b, grs_r, gm) @ up * 1e9
        series = {"lipe_newtonian": lipe,
                  "pygtide_default_irigid0_cat8": run_pygtide(lat,lon,elev,start),
                  "pygtide_four_unit_bands_irigid0_cat8": run_pygtide(lat,lon,elev,start,groups=GROUPS),
                  "pygtide_true_irigid1_cat8": run_pygtide(lat,lon,elev,start,irigid=1),
                  "pygtide_true_irigid1_four_bands_cat8": run_pygtide(lat,lon,elev,start,irigid=1,groups=GROUPS),
                  "pygtide_true_irigid1_cat7": run_pygtide(lat,lon,elev,start,irigid=1,catalogue=7),
                  "lipe_geocentric_radial": radial, "lipe_eterna_ellipsoid": grs}
        table = pd.DataFrame({"timestamp_utc": frame.index.astype(str), **series})
        comparisons = {}
        for name, values in series.items():
            if name == "lipe_newtonian": continue
            table[f"residual_lipe_minus_{name}"] = lipe-values
            comparisons[f"lipe_minus_{name}"] = metrics(lipe, values)
            f, a = spectrum(lipe-values)
            spectra.extend({"site":site, "comparison":f"lipe_minus_{name}",
                            "frequency_cpd":float(ff), "amplitude_nm_s2":float(aa)}
                           for ff, aa in zip(f[1:], a[1:]))
        names = list(series)
        corr = np.corrcoef(np.vstack([series[n] for n in names]))
        report["sites"][site] = {"coordinates": {"lat":lat,"lon":lon,"elevation_m":elev},
            "start_utc":start, "comparisons":comparisons,
            "irigid_group_invariance_max_abs_nm_s2": float(np.max(np.abs(series["pygtide_true_irigid1_cat8"]-series["pygtide_true_irigid1_four_bands_cat8"]))),
            "pairwise_correlations": {a:{b:float(corr[i,j]) for j,b in enumerate(names)} for i,a in enumerate(names)}}
        table.to_csv(out/f"{site}.csv", index=False)
    pd.DataFrame(spectra).to_csv(out/"spectra.csv", index=False)
    (out/"metrics.json").write_text(json.dumps(report, indent=2)+"\n")


if __name__ == "__main__": main()
