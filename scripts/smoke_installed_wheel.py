#!/usr/bin/env python3
"""Smoke-test an installed LIPE wheel, including all output formats."""
from __future__ import annotations

import argparse
from pathlib import Path

import lunar_physics
from lunar_physics import calculate
from lunar_physics.cli import write_output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("lipe-wheel-smoke"))
    args = parser.parse_args()
    frame = calculate(47.6062, -122.3321, 56.0,
                      "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", 15)
    assert len(frame) == 4
    assert lunar_physics.__version__ == "0.2.0"
    assert frame.attrs["metadata"]["ephemeris_sha256"]
    write_output(frame, args.output_dir / "smoke.csv")
    write_output(frame, args.output_dir / "smoke.json")
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        pass
    else:
        write_output(frame, args.output_dir / "smoke.parquet")
    print("installed wheel smoke test passed", lunar_physics.__version__)


if __name__ == "__main__":
    main()
