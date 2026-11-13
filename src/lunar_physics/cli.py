"""Command-line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .api import calculate


def _records(frame):
    data = frame.reset_index()
    data["time_utc"] = data["time_utc"].astype(str)
    return data.to_dict(orient="records")


def write_output(frame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = frame.attrs["metadata"]
    suffix = path.suffix.lower()
    if suffix == ".json":
        path.write_text(json.dumps({"metadata": metadata, "records": _records(frame)}, indent=2), encoding="utf-8")
    elif suffix == ".csv":
        frame.to_csv(path)
    elif suffix in (".parquet", ".pq"):
        frame.to_parquet(path)
    else:
        raise ValueError("output extension must be .json, .csv, .parquet, or .pq")
    if suffix != ".json":
        path.with_suffix(path.suffix + ".metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="lunar-physics")
    subparsers = parser.add_subparsers(dest="command", required=True)
    compute = subparsers.add_parser("compute")
    compute.add_argument("--lat", type=float, required=True)
    compute.add_argument("--lon", type=float, required=True)
    compute.add_argument("--elevation-m", type=float, default=0.0)
    compute.add_argument("--start", required=True)
    compute.add_argument("--end", required=True)
    compute.add_argument("--step-minutes", type=float, default=15)
    compute.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    frame = calculate(args.lat, args.lon, args.elevation_m, args.start, args.end, args.step_minutes)
    write_output(frame, args.output)
