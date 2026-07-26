"""Load and clean stops from a Dublin GTFS feed."""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd

from gtfs_utils import ensure_parent, read_gtfs_table


def load_stops(feed: str | Path) -> gpd.GeoDataFrame:
    """Return valid GTFS stops as point features in WGS84 (EPSG:4326)."""
    stops = read_gtfs_table(feed, "stops.txt", dtype={"stop_id": "string"})
    required = {"stop_id", "stop_name", "stop_lat", "stop_lon"}
    missing = required.difference(stops.columns)
    if missing:
        raise ValueError(f"stops.txt is missing columns: {', '.join(sorted(missing))}")

    stops["stop_lat"] = pd.to_numeric(stops["stop_lat"], errors="coerce")
    stops["stop_lon"] = pd.to_numeric(stops["stop_lon"], errors="coerce")
    stops = stops.dropna(subset=["stop_id", "stop_lat", "stop_lon"]).copy()
    stops = stops[stops["stop_lat"].between(-90, 90) & stops["stop_lon"].between(-180, 180)]
    return gpd.GeoDataFrame(
        stops,
        geometry=gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"]),
        crs="EPSG:4326",
    )


def save_stops(stops: gpd.GeoDataFrame, output: str | Path) -> Path:
    output = ensure_parent(output)
    stops.to_file(output, driver="GeoJSON")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gtfs", default="data/raw/gtfs", help="GTFS directory or ZIP")
    parser.add_argument("--output", default="data/processed/stops.geojson")
    args = parser.parse_args()
    stops = load_stops(args.gtfs)
    output = save_stops(stops, args.output)
    print(f"Saved {len(stops):,} stops to {output}")


if __name__ == "__main__":
    main()
