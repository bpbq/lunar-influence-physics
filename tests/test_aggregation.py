import numpy as np
import pandas as pd

from lunar_physics.aggregation import daily_summaries, summarize, vector_summary


def test_missing_gap_is_not_integrated():
    idx = pd.date_range("2026-01-01", periods=4, freq="15min", tz="UTC")
    series = pd.Series([1.0, 1.0, np.nan, 1.0], index=idx)
    result = summarize(series)
    assert result["coverage"] == 0.75
    assert result["integrated_absolute"] == 900.0
    assert result["integrated_duration_seconds"] == 900.0
    assert result["excluded_gap_count"] == 1
    assert result["expected_step_source"].startswith("inferred")


def test_irregular_large_timestamp_gap_is_not_integrated_by_default():
    idx = pd.to_datetime([
        "2026-01-01T00:00:00Z", "2026-01-01T00:10:00Z",
        "2026-01-01T00:21:00Z", "2026-01-01T03:00:00Z",
    ])
    result = summarize(pd.Series([1.0, 1.0, 1.0, 100.0], index=idx))
    assert result["expected_step_seconds"] == 600.0
    assert result["integrated_absolute"] == 600.0
    assert result["integrated_duration_seconds"] == 600.0
    assert result["excluded_gap_count"] == 2


def test_interval_boundaries_are_not_extrapolated():
    idx = pd.to_datetime(["2026-01-01T00:15:00Z", "2026-01-01T00:30:00Z"])
    result = summarize(
        pd.Series([2.0, 2.0], index=idx), expected_step="15min",
        interval_start="2026-01-01T00:00:00Z",
        interval_end="2026-01-01T01:00:00Z",
    )
    assert result["expected_count"] == 4
    assert result["coverage"] == 0.5
    assert result["integrated_absolute"] == 1800.0
    assert result["integrated_duration_seconds"] == 900.0
    assert result["interval_semantics"] == "half-open; no boundary extrapolation"


def test_vector_mean_semantics():
    idx = pd.date_range("2026-01-01", periods=2, freq="h", tz="UTC")
    frame = pd.DataFrame({"x": [1, -1], "y": [0, 0], "z": [0, 0]}, index=idx)
    result = vector_summary(frame, ("x", "y", "z"))
    assert result["mean_magnitude"] == 1.0
    assert result["magnitude_of_mean"] == 0.0


def test_dst_local_days_keep_real_sample_counts():
    idx = pd.date_range("2026-03-08T05:00Z", "2026-03-09T04:00Z", freq="h", inclusive="left")
    frame = pd.DataFrame({"x": 1.0}, index=idx)
    result = daily_summaries(frame, ["x"], timezone="America/New_York")
    assert result["2026-03-08"]["x"]["count"] == 23


def test_dst_fall_day_has_25_real_hours():
    idx = pd.date_range("2026-11-01T04:00Z", "2026-11-02T05:00Z", freq="h", inclusive="left")
    frame = pd.DataFrame({"x": 1.0}, index=idx)
    result = daily_summaries(frame, ["x"], timezone="America/New_York")
    assert result["2026-11-01"]["x"]["count"] == 25
    assert result["2026-11-01"]["x"]["expected_count"] == 25


def test_single_timestamp_daily_summary_reports_unknown_cadence():
    idx = pd.to_datetime(["2026-01-01T12:00:00Z"])
    result = daily_summaries(pd.DataFrame({"x": [3.0]}, index=idx), ["x"])
    summary = result["2026-01-01"]["x"]
    assert summary["count"] == 1
    assert summary["status"] == "insufficient_timestamps_for_step"
    assert summary["coverage"] is None
    assert summary["integrated_absolute"] is None
