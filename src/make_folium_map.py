"""Build an interactive map of Dublin stops, catchments, and service frequency."""

from __future__ import annotations

import argparse
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
from branca.colormap import linear

from gtfs_utils import ensure_parent


def make_map(
    stops: gpd.GeoDataFrame,
    catchments: gpd.GeoDataFrame,
    frequency: pd.DataFrame,
) -> folium.Map:
    stops = stops.merge(frequency, on="stop_id", how="left")
    stops[["departures", "trips"]] = stops[["departures", "trips"]].fillna(0).astype(int)
    centre = [53.3498, -6.2603] if stops.empty else [stops.geometry.y.mean(), stops.geometry.x.mean()]
    transit_map = folium.Map(location=centre, zoom_start=11, tiles="CartoDB positron")

    radius = int(catchments["catchment_m"].iloc[0]) if "catchment_m" in catchments and not catchments.empty else 500
    folium.GeoJson(
        catchments,
        name=f"{radius} m stop catchments",
        style_function=lambda _: {"fillColor": "#3186cc", "color": "#3186cc", "weight": 1, "fillOpacity": 0.08},
    ).add_to(transit_map)

    maximum = max(1, int(stops["departures"].max()))
    colours = linear.YlOrRd_09.scale(0, maximum)
    colours.caption = "Scheduled departures in the GTFS feed"
    colours.add_to(transit_map)
    stop_layer = folium.FeatureGroup(name="Stops and frequency", show=True)
    for row in stops.itertuples():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=max(3, min(10, 3 + row.departures ** 0.5 / 4)),
            color=colours(row.departures),
            fill=True,
            fill_opacity=0.8,
            weight=1,
            tooltip=str(row.stop_name),
            popup=folium.Popup(
                f"<b>{row.stop_name}</b><br>Stop ID: {row.stop_id}<br>"
                f"Scheduled departures: {row.departures}<br>Distinct trips: {row.trips}",
                max_width=300,
            ),
        ).add_to(stop_layer)
    stop_layer.add_to(transit_map)
    folium.LayerControl(collapsed=False).add_to(transit_map)
    return transit_map


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stops", default="data/processed/stops.geojson")
    parser.add_argument("--catchments", default="data/processed/stop_catchments.geojson")
    parser.add_argument("--frequency", default="data/processed/stop_frequency.csv")
    parser.add_argument("--output", default="outputs/dublin_transit_map.html")
    args = parser.parse_args()
    transit_map = make_map(
        gpd.read_file(args.stops),
        gpd.read_file(args.catchments),
        pd.read_csv(args.frequency, dtype={"stop_id": "string"}),
    )
    output = ensure_parent(args.output)
    transit_map.save(output)
    print(f"Saved interactive map to {output}")


if __name__ == "__main__":
    main()
