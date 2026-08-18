"""Create a regular grid and score potential public-transport gaps in Dublin."""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box
from sklearn.neighbors import NearestNeighbors

from create_catchments import IRISH_TRANSVERSE_MERCATOR
from gtfs_utils import ensure_parent


# A deliberately explicit first-pass study area. It covers Dublin city and county
# without pretending that a GTFS feed (which may be national) supplies a boundary.
DUBLIN_BOUNDS_WGS84 = (-6.55, 53.15, -6.05, 53.65)
ACCESS_LABELS = ["Good access", "Moderate access", "Poor access", "Potential transit gap"]


def create_analysis_grid(cell_size_metres: float = 1000) -> gpd.GeoDataFrame:
    """Create square cells covering the documented Dublin study area."""
    if cell_size_metres <= 0:
        raise ValueError("cell_size_metres must be greater than zero")
    boundary = gpd.GeoSeries([box(*DUBLIN_BOUNDS_WGS84)], crs="EPSG:4326").to_crs(
        IRISH_TRANSVERSE_MERCATOR
    ).iloc[0]
    minx, miny, maxx, maxy = boundary.bounds
    cells = [
        box(x, y, min(x + cell_size_metres, maxx), min(y + cell_size_metres, maxy))
        for x in np.arange(minx, maxx, cell_size_metres)
        for y in np.arange(miny, maxy, cell_size_metres)
    ]
    grid = gpd.GeoDataFrame({"geometry": cells}, crs=IRISH_TRANSVERSE_MERCATOR)
    grid = grid[grid.geometry.centroid.within(boundary)].reset_index(drop=True)
    grid.insert(0, "cell_id", [f"DUB-{number:05d}" for number in range(1, len(grid) + 1)])
    return grid


def analyse_hotspots(
    stops: gpd.GeoDataFrame,
    frequency: pd.DataFrame,
    cell_size_metres: float = 1000,
    service_radius_metres: float = 800,
) -> gpd.GeoDataFrame:
    """Measure stop proximity/service near each grid centroid and score access."""
    if stops.empty:
        raise ValueError("At least one GTFS stop is required")
    if service_radius_metres <= 0:
        raise ValueError("service_radius_metres must be greater than zero")

    grid = create_analysis_grid(cell_size_metres)
    projected_stops = stops.to_crs(IRISH_TRANSVERSE_MERCATOR).copy()
    projected_stops["stop_id"] = projected_stops["stop_id"].astype("string")
    counts = frequency.copy()
    counts["stop_id"] = counts["stop_id"].astype("string")
    projected_stops = projected_stops.merge(counts[["stop_id", "departures"]], on="stop_id", how="left")
    projected_stops["departures"] = projected_stops["departures"].fillna(0).astype(float)

    centre_xy = np.column_stack((grid.geometry.centroid.x, grid.geometry.centroid.y))
    stop_xy = np.column_stack((projected_stops.geometry.x, projected_stops.geometry.y))
    neighbours = NearestNeighbors().fit(stop_xy)
    nearest_distance, _ = neighbours.kneighbors(centre_xy, n_neighbors=1)
    nearby_indices = neighbours.radius_neighbors(
        centre_xy, radius=service_radius_metres, return_distance=False
    )
    nearby_departures = np.array(
        [projected_stops["departures"].iloc[index].sum() for index in nearby_indices]
    )

    grid["nearest_stop_m"] = nearest_distance[:, 0].round(1)
    grid["stops_within_800m"] = [len(index) for index in nearby_indices]
    grid["nearby_departures"] = nearby_departures.astype(int)

    # Both components are capped to keep outliers from dominating. Population is
    # intentionally reserved as a future component and currently has zero weight.
    distance_need = np.clip(grid["nearest_stop_m"] / 1600.0, 0, 1)
    positive_service = nearby_departures[nearby_departures > 0]
    service_reference = float(np.percentile(positive_service, 90)) if len(positive_service) else 1.0
    frequency_access = np.clip(np.log1p(nearby_departures) / np.log1p(service_reference), 0, 1)
    frequency_need = 1 - frequency_access
    population_need_placeholder = np.zeros(len(grid))
    grid["gap_score"] = (
        100 * (0.5 * distance_need + 0.5 * frequency_need + 0.0 * population_need_placeholder)
    ).round(1)
    grid["access_class"] = pd.cut(
        grid["gap_score"], bins=[-np.inf, 25, 50, 75, np.inf], labels=ACCESS_LABELS
    ).astype("string")
    grid["rank"] = grid["gap_score"].rank(method="first", ascending=False).astype(int)
    return grid.to_crs("EPSG:4326")


def save_hotspots(hotspots: gpd.GeoDataFrame, geojson: str | Path, ranking: str | Path) -> None:
    """Write spatial results and a highest-need-first tabular ranking."""
    hotspots.to_file(ensure_parent(geojson), driver="GeoJSON")
    columns = [
        "rank", "cell_id", "gap_score", "access_class", "nearest_stop_m",
        "stops_within_800m", "nearby_departures",
    ]
    hotspots.sort_values("rank")[columns].to_csv(ensure_parent(ranking), index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stops", default="data/processed/stops.geojson")
    parser.add_argument("--frequency", default="data/processed/stop_frequency.csv")
    parser.add_argument("--cell-size", type=float, default=1000)
    parser.add_argument("--service-radius", type=float, default=800)
    parser.add_argument("--geojson", default="outputs/underserved_hotspots.geojson")
    parser.add_argument("--ranking", default="outputs/hotspot_ranking.csv")
    args = parser.parse_args()
    hotspots = analyse_hotspots(
        gpd.read_file(args.stops),
        pd.read_csv(args.frequency, dtype={"stop_id": "string"}),
        args.cell_size,
        args.service_radius,
    )
    save_hotspots(hotspots, args.geojson, args.ranking)
    print(f"Saved {len(hotspots):,} scored grid cells")


if __name__ == "__main__":
    main()
