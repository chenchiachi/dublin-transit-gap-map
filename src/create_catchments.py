"""Create simple straight-line catchment buffers around transit stops."""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd

from gtfs_utils import ensure_parent

IRISH_TRANSVERSE_MERCATOR = "EPSG:2157"


def create_catchments(stops: gpd.GeoDataFrame, radius_metres: float = 500) -> gpd.GeoDataFrame:
    """Buffer stops by a distance in metres and return polygons in WGS84."""
    if stops.crs is None:
        raise ValueError("Stops must have a coordinate reference system")
    if radius_metres <= 0:
        raise ValueError("radius_metres must be greater than zero")

    projected = stops.to_crs(IRISH_TRANSVERSE_MERCATOR)
    catchments = projected.copy()
    catchments["catchment_m"] = float(radius_metres)
    catchments["geometry"] = projected.geometry.buffer(radius_metres)
    return catchments.to_crs("EPSG:4326")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stops", default="data/processed/stops.geojson")
    parser.add_argument("--radius", type=float, default=500, help="Buffer radius in metres")
    parser.add_argument("--output", default="data/processed/stop_catchments.geojson")
    args = parser.parse_args()
    stops = gpd.read_file(args.stops)
    catchments = create_catchments(stops, args.radius)
    output = ensure_parent(args.output)
    catchments.to_file(output, driver="GeoJSON")
    print(f"Saved {len(catchments):,} catchments to {output}")


if __name__ == "__main__":
    main()
