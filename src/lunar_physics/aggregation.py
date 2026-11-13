"""Time aggregation without implicit interpolation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _seconds(index: pd.DatetimeIndex) -> np.ndarray:
    return np.array([stamp.timestamp() for stamp in index], dtype=float)


def _resolve_step(index: pd.DatetimeIndex, expected_step) -> tuple[pd.Timedelta, str]:
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError("series index must be a DatetimeIndex")
    if index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError("timestamps must be unique and strictly increasing")
    if expected_step is not None:
        step = pd.Timedelta(expected_step)
        if step <= pd.Timedelta(0):
            raise ValueError("expected_step must be positive")
        return step, "explicit"
    if len(index) < 2:
        raise ValueError("expected_step is required when fewer than two timestamps are present")
    deltas = np.diff(_seconds(index))
    if np.any(deltas <= 0):
        raise ValueError("timestamps must be unique and strictly increasing")
    # The shortest observed gap is the conservative cadence: a missing sample
    # can only lengthen a gap, so it cannot make a large gap look integrable.
    cadence = float(deltas.min())
    return pd.Timedelta(seconds=cadence), "inferred_from_minimum_timestamp_gap"


def summarize(
    series: pd.Series,
    *,
    expected_step: pd.Timedelta | str | None = None,
    interval_start=None,
    interval_end=None,
) -> dict:
    """Summarize samples without interpolating or extrapolating.

    The integration interval is half-open. Trapezoids are included only when
    both endpoints are finite and separated by at most 1.01 nominal steps.
    No value is extrapolated from a sample to either interval boundary.
    Coverage is finite samples divided by the number of nominal sample slots.
    """
    values = series.astype(float)
    step, step_source = _resolve_step(values.index, expected_step)
    if values.empty and (interval_start is None or interval_end is None):
        raise ValueError("empty series requires explicit interval_start and interval_end")
    start = pd.Timestamp(interval_start) if interval_start is not None else values.index[0]
    end = pd.Timestamp(interval_end) if interval_end is not None else values.index[-1] + step
    if end <= start:
        raise ValueError("interval_end must be later than interval_start")
    values = values.loc[(values.index >= start) & (values.index < end)]
    interval_seconds = (end - start).total_seconds()
    expected_count = max(1, int(np.ceil(interval_seconds / step.total_seconds() - 1e-12)))
    valid = values.dropna()

    base = {
        "count": int(valid.size),
        "expected_count": expected_count,
        "coverage": float(min(valid.size / expected_count, 1.0)),
        "expected_step_seconds": float(step.total_seconds()),
        "expected_step_source": step_source,
        "interval_start": start.isoformat(),
        "interval_end": end.isoformat(),
        "interval_semantics": "half-open; no boundary extrapolation",
        "integrated_duration_seconds": 0.0,
        "excluded_gap_count": 0,
    }
    if valid.empty:
        return base

    seconds = _seconds(valid.index)
    x = valid.to_numpy()
    gaps = np.diff(seconds)
    adjacent = gaps <= step.total_seconds() * 1.01
    integral = float(np.sum((np.abs(x[:-1]) + np.abs(x[1:])) * 0.5 * gaps * adjacent))
    derivative = np.diff(x)[adjacent] / gaps[adjacent] if adjacent.any() else np.array([])
    return {
        **base,
        "integrated_duration_seconds": float(gaps[adjacent].sum()),
        "excluded_gap_count": int((~adjacent).sum()),
        "mean": float(x.mean()), "signed_mean": float(x.mean()),
        "min": float(x.min()), "max": float(x.max()),
        "peak_to_peak": float(x.max() - x.min()),
        "rms": float(np.sqrt(np.mean(x * x))),
        "mean_absolute": float(np.mean(np.abs(x))),
        "integrated_absolute": integral,
        "min_time": valid.idxmin().isoformat(), "max_time": valid.idxmax().isoformat(),
        "time_derivative_min": float(derivative.min()) if derivative.size else None,
        "time_derivative_max": float(derivative.max()) if derivative.size else None,
        "time_derivative_rms": float(np.sqrt(np.mean(derivative ** 2))) if derivative.size else None,
    }


def interval_summary(frame: pd.DataFrame, start, end, columns=None, *, expected_step=None) -> dict:
    """Summarize a half-open interval `[start, end)`."""
    columns = columns or list(frame.select_dtypes(include=[np.number]).columns)
    return {
        column: summarize(
            frame[column], expected_step=expected_step,
            interval_start=start, interval_end=end,
        )
        for column in columns
    }


def daily_summaries(frame: pd.DataFrame, columns=None, *, timezone="UTC", expected_step=None) -> dict:
    """Aggregate by UTC or IANA local calendar day, respecting DST."""
    local = frame.tz_convert(timezone)
    shared_step = expected_step
    if shared_step is None and len(local.index) >= 2:
        shared_step, _ = _resolve_step(local.index, None)
    result = {}
    for day, group in local.groupby(local.index.date):
        columns_ = columns or list(group.select_dtypes(include=[np.number]).columns)
        start = pd.Timestamp(str(day), tz=timezone)
        end = start + pd.DateOffset(days=1)
        if shared_step is None:
            result[str(day)] = {c: {
                "count": int(group[c].notna().sum()),
                "status": "insufficient_timestamps_for_step",
                "expected_count": None, "coverage": None,
                "expected_step_seconds": None, "expected_step_source": "unavailable",
                "interval_start": start.isoformat(), "interval_end": end.isoformat(),
                "interval_semantics": "half-open; cadence unknown; no integration",
                "integrated_absolute": None, "integrated_duration_seconds": 0.0,
            } for c in columns_}
        else:
            result[str(day)] = {
                c: summarize(group[c], expected_step=shared_step,
                             interval_start=start, interval_end=end)
                for c in columns_
            }
            if expected_step is None:
                for summary in result[str(day)].values():
                    summary["expected_step_source"] = "inferred_from_full_frame_minimum_gap"
    return result


def vector_summary(frame: pd.DataFrame, columns: tuple[str, str, str]) -> dict:
    """Keep component mean, mean magnitude, and magnitude of mean distinct."""
    vectors = frame.loc[:, columns].dropna().to_numpy(float)
    mean_vector = vectors.mean(axis=0)
    return {
        "mean_vector": mean_vector.tolist(),
        "mean_magnitude": float(np.linalg.norm(vectors, axis=1).mean()),
        "magnitude_of_mean": float(np.linalg.norm(mean_vector)),
    }


def event_intervals(events, start_event: str, end_event: str):
    """Pair ordered event records into half-open intervals, without interpolation."""
    starts = []
    intervals = []
    for event in sorted(events, key=lambda item: item["time_utc"]):
        if event["event"] == start_event:
            starts.append(pd.Timestamp(event["time_utc"]))
        elif event["event"] == end_event and starts:
            start = starts.pop(0)
            end = pd.Timestamp(event["time_utc"])
            if end > start:
                intervals.append((start, end))
    return intervals


def sunset_to_sunrise_summaries(frame, events, columns=None, *, expected_step=None):
    """Summarize complete Sun-set to Sun-rise intervals."""
    return {
        f"{start.isoformat()}/{end.isoformat()}": interval_summary(
            frame, start, end, columns, expected_step=expected_step
        )
        for start, end in event_intervals(events, "sun_set", "sun_rise")
    }
