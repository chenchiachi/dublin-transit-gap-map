"""Run the complete first-pass Dublin GTFS mapping pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from calculate_service_frequency import calculate_frequency
from analyze_hotspots import analyse_hotspots, save_hotspots
from create_catchments import create_catchments
from gtfs_utils import ensure_parent
from load_gtfs_stops import load_stops, save_stops
from make_folium_map import make_map


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gtfs", default="data/raw/gtfs", help="GTFS directory or ZIP")
    parser.add_argument("--radius", type=float, default=500, help="Catchment radius in metres")
    parser.add_argument("--grid-size", type=float, default=1000, help="Hotspot grid size in metres")
    args = parser.parse_args()

    stops = load_stops(args.gtfs)
    catchments = create_catchments(stops, args.radius)
    frequency = calculate_frequency(args.gtfs)
    hotspots = analyse_hotspots(stops, frequency, args.grid_size, 800)

    save_stops(stops, "data/processed/stops.geojson")
    catchment_path = ensure_parent("data/processed/stop_catchments.geojson")
    catchments.to_file(catchment_path, driver="GeoJSON")
    frequency_path = ensure_parent("data/processed/stop_frequency.csv")
    frequency.to_csv(frequency_path, index=False)
    save_hotspots(
        hotspots,
        "outputs/underserved_hotspots.geojson",
        "outputs/hotspot_ranking.csv",
    )
    map_path = ensure_parent("outputs/dublin_transit_map.html")
    make_map(stops, catchments, frequency, hotspots).save(map_path)
    print(f"Processed {len(stops):,} stops and saved {map_path}")


if __name__ == "__main__":
    main()
