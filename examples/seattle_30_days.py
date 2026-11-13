"""Generate a 30-day Seattle dataset and three diagnostic plots."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from lunar_physics import calculate
from lunar_physics.cli import write_output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/seattle"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = calculate(47.6062, -122.3321, 56.0, "2026-01-01T00:00:00Z", "2026-01-31T00:00:00Z", 15)
    write_output(data, args.output_dir / "seattle_30_days.parquet")
    plots = {
        "gravity.png": ["moon_tidal_vertical_nm_s2", "sun_tidal_vertical_nm_s2", "total_tidal_vertical_nm_s2"],
        "moon_position.png": ["moon_altitude_deg", "moon_azimuth_deg"],
        "moon_illuminance.png": ["moon_outdoor_illuminance_lux"],
    }
    for filename, columns in plots.items():
        axes = data[columns].plot(figsize=(12, 4), title=filename.removesuffix(".png"))
        axes.set_xlabel("UTC")
        axes.figure.tight_layout()
        axes.figure.savefig(args.output_dir / filename, dpi=150)
        plt.close(axes.figure)


if __name__ == "__main__":
    main()
