"""Calculate a simple scheduled-departure count for every GTFS stop."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from gtfs_utils import ensure_parent, read_gtfs_table


def calculate_frequency(feed: str | Path) -> pd.DataFrame:
    """Count stop-time rows per stop (the whole feed schedule, not live service)."""
    stop_times = read_gtfs_table(
        feed,
        "stop_times.txt",
        dtype={"stop_id": "string", "trip_id": "string"},
        usecols=lambda column: column in {"stop_id", "trip_id", "departure_time", "arrival_time"},
    )
    if "stop_id" not in stop_times:
        raise ValueError("stop_times.txt is missing stop_id")

    time_column = "departure_time" if "departure_time" in stop_times else "arrival_time"
    if time_column not in stop_times:
        raise ValueError("stop_times.txt needs departure_time or arrival_time")
    valid = stop_times.dropna(subset=["stop_id", time_column])
    result = valid.groupby("stop_id", as_index=False).agg(
        departures=(time_column, "count"),
        trips=("trip_id", "nunique") if "trip_id" in valid else (time_column, "count"),
    )
    return result.sort_values(["departures", "stop_id"], ascending=[False, True])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gtfs", default="data/raw/gtfs", help="GTFS directory or ZIP")
    parser.add_argument("--output", default="data/processed/stop_frequency.csv")
    args = parser.parse_args()
    frequency = calculate_frequency(args.gtfs)
    output = ensure_parent(args.output)
    frequency.to_csv(output, index=False)
    print(f"Saved frequency counts for {len(frequency):,} stops to {output}")


if __name__ == "__main__":
    main()
