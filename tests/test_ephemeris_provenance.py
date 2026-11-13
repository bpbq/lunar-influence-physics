from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from lunar_physics import calculate
from lunar_physics.ephemeris import load_ephemeris, sha256_file


_IERS_LINE = bytearray(
    b"73 1 2 41684.00 I  0.120733 0.009786  0.136966 0.015902  "
    b"I 0.8084178 0.0002710  0.0000 0.1916  P    -0.766    0.199    "
    b"-0.720    0.300   .143000   .137000   .8075000   -18.637    -3.667  "
)


def _write_artificial_iers(
    path, *, x_offset=0.1, y_offset=0.2, dut1_offset=0.0,
    start_mjd=41684, end_mjd=42049, leap_mjds=(42048,), omit_mjd=None,
):
    lines = []
    epoch = date(1858, 11, 17)
    for mjd in range(start_mjd, end_mjd + 1):
        if mjd == omit_mjd:
            continue
        offset = mjd - start_mjd
        day = epoch + timedelta(days=mjd)
        leap_count = sum(mjd >= leap_mjd for leap_mjd in leap_mjds)
        x = x_offset + offset * 0.0001
        y = y_offset + offset * 0.0001
        dut1 = -0.6 + dut1_offset + offset * 0.001 + leap_count
        line = _IERS_LINE.copy()
        line[0:6] = f"{day.year % 100:02d}{day.month:2d}{day.day:2d}".encode()
        line[6:15] = f"{float(mjd):9.2f}".encode()
        line[18:27] = f"{x:9.6f}".encode()
        line[37:46] = f"{y:9.6f}".encode()
        line[58:68] = f"{dut1:10.7f}".encode()
        lines.append(bytes(line))
    path.write_bytes(b"\n".join(lines) + b"\n")


def test_default_timescale_is_pinned_offline_snapshot():
    _, _, metadata = load_ephemeris()
    assert metadata["timescale_mode"] == "builtin_snapshot"
    assert metadata["earth_orientation_sha256"].startswith("c7d7536d")
    assert metadata["timescale_switching"].startswith("explicit only")
    assert "zero" in metadata["polar_motion"]


def test_fixed_iers_snapshot_has_provenance_and_polar_motion():
    _, _, metadata = load_ephemeris(timescale_mode="iers_snapshot")
    assert metadata["earth_orientation_sha256"].startswith("d0d9c214")
    assert metadata["timescale_mode"] == "iers_snapshot"
    assert "installed" in metadata["polar_motion"]
    assert metadata["earth_orientation_coverage_start_utc"].startswith("1973-01-02")
    assert metadata["earth_orientation_reliable_end_utc"].startswith("2025-08-21")
    assert metadata["earth_orientation_coverage_end_utc"].startswith("2026-08-29")
    assert metadata["earth_orientation_prediction_start_utc"].startswith("2025-08-22")
    assert metadata["earth_orientation_out_of_reliable_coverage_policy"] == "error"


def test_updateable_mode_requires_an_explicit_file():
    with pytest.raises(ValueError, match="requires eop_path"):
        load_ephemeris(timescale_mode="iers_file")


def test_iers_file_uses_one_explicit_arbitrarily_named_file(tmp_path):
    table_a = tmp_path / "chosen-a.custom-eop"
    table_b = tmp_path / "chosen-b.unusual-name"
    decoy = tmp_path / "finals2000A.all"
    _write_artificial_iers(
        table_a, x_offset=0.10, y_offset=0.20, dut1_offset=0.0,
    )
    _write_artificial_iers(
        table_b, x_offset=0.40, y_offset=0.50, dut1_offset=-0.10,
    )
    # The old Loader path silently used this conventional filename for UT1 and
    # Delta T while using the selected file only for polar motion.
    _write_artificial_iers(
        decoy, x_offset=0.70, y_offset=0.80, dut1_offset=0.10,
    )

    _, ts_a, metadata_a = load_ephemeris(
        timescale_mode="iers_file", eop_path=table_a,
    )
    _, ts_b, metadata_b = load_ephemeris(
        timescale_mode="iers_file", eop_path=table_b,
    )

    np.testing.assert_allclose(ts_a.delta_t_table[1][[0, -1]], (44.784, 44.419))
    np.testing.assert_allclose(ts_b.delta_t_table[1][[0, -1]], (44.884, 44.519))
    np.testing.assert_allclose(ts_a.polar_motion_table[1][[0, -1]], (0.10, 0.1365))
    np.testing.assert_allclose(ts_a.polar_motion_table[2][[0, -1]], (0.20, 0.2365))
    np.testing.assert_allclose(ts_b.polar_motion_table[1][[0, -1]], (0.40, 0.4365))
    np.testing.assert_allclose(ts_b.polar_motion_table[2][[0, -1]], (0.50, 0.5365))

    assert metadata_a["earth_orientation_path"] == str(table_a.resolve())
    assert metadata_b["earth_orientation_path"] == str(table_b.resolve())
    assert metadata_a["earth_orientation_sha256"] == sha256_file(table_a)
    assert metadata_b["earth_orientation_sha256"] == sha256_file(table_b)
    assert metadata_a["earth_orientation_record_count"] == 366
    assert metadata_b["earth_orientation_record_count"] == 366
    assert metadata_a["ut1_utc_last_seconds"] == pytest.approx(0.765)
    assert metadata_b["ut1_utc_last_seconds"] == pytest.approx(0.665)
    assert metadata_a["delta_t_last_seconds"] == pytest.approx(44.419)
    assert metadata_b["delta_t_last_seconds"] == pytest.approx(44.519)
    assert metadata_a["polar_motion_last_x_arcseconds"] == pytest.approx(0.1365)
    assert metadata_b["polar_motion_last_y_arcseconds"] == pytest.approx(0.5365)
    assert table_a.name in metadata_a["earth_orientation_source"]
    assert table_b.name in metadata_b["earth_orientation_source"]


def test_partial_late_iers_history_with_one_leap_jump_is_rejected(tmp_path):
    partial = tmp_path / "partial-late-finals.data"
    _write_artificial_iers(
        partial, start_mjd=57000, end_mjd=57205, leap_mjds=(57204,),
    )
    with pytest.raises(ValueError, match="truncated.*MJD 41684"):
        load_ephemeris(timescale_mode="iers_file", eop_path=partial)


def test_iers_calendar_gap_and_wrong_leap_date_are_rejected(tmp_path):
    gap = tmp_path / "calendar-gap.data"
    _write_artificial_iers(gap, omit_mjd=41800)
    with pytest.raises(ValueError, match="calendar-daily and contiguous"):
        load_ephemeris(timescale_mode="iers_file", eop_path=gap)

    wrong_leap = tmp_path / "wrong-leap-date.data"
    _write_artificial_iers(wrong_leap, leap_mjds=(42047,))
    with pytest.raises(ValueError, match="jumps do not match"):
        load_ephemeris(timescale_mode="iers_file", eop_path=wrong_leap)


def test_iers_calendar_fields_must_match_mjd(tmp_path):
    invalid_date = tmp_path / "invalid-calendar.data"
    _write_artificial_iers(invalid_date)
    content = invalid_date.read_bytes()
    invalid_date.write_bytes(b"73 230" + content[6:])
    with pytest.raises(ValueError, match="calendar date does not match"):
        load_ephemeris(timescale_mode="iers_file", eop_path=invalid_date)


def test_calculate_rejects_dates_outside_reliable_real_iers_coverage():
    with pytest.raises(ValueError, match="outside reliable observed IERS coverage"):
        calculate(
            47.6062, -122.3321, 56.0,
            "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", 15,
            timescale_mode="iers_snapshot",
        )


def test_calculate_records_requested_interval_inside_custom_iers_coverage(tmp_path):
    table = tmp_path / "complete-custom-eop.data"
    _write_artificial_iers(table)
    result = calculate(
        0.0, 0.0, 0.0,
        "1973-06-01T00:00:00Z", "1973-06-01T01:00:00Z", 15,
        timescale_mode="iers_file", eop_path=table,
    )
    metadata = result.attrs["metadata"]
    assert metadata["earth_orientation_requested_interval_status"] == \
        "within_reliable_coverage"
    assert metadata["earth_orientation_requested_start_utc"] == \
        "1973-06-01T00:00:00+00:00"
    assert metadata["earth_orientation_requested_end_utc"] == \
        "1973-06-01T01:00:00+00:00"
