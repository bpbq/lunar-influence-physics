# Seattle 30-day example

Run `python examples/seattle_30_days.py --output-dir artifacts/seattle` to
calculate 2,880 samples at 15-minute cadence for January 2026. It produces:

- `seattle_30_days.parquet` and its model/provenance metadata;
- `gravity.png`, with separate lunar, solar, and total vertical acceleration;
- `moon_position.png`, with apparent altitude and azimuth;
- `moon_illuminance.png`, with modeled clear-sky outdoor horizontal lux.

The generated artifacts are intentionally ignored by Git because the Parquet
file is deterministic and about 2.5 MB. The illuminance plot is a modeled
outdoor quantity under simplified atmospheric assumptions.
