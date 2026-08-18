"""Build a layered interactive map of Dublin stops and service frequency."""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
from branca.element import Element
from folium.plugins import HeatMap, MarkerCluster

from gtfs_utils import ensure_parent


DUBLIN_CENTRE = [53.3498, -6.2603]
FREQUENCY_COLOURS = {
    "Low frequency": "#2c7bb6",
    "Medium frequency": "#fdae61",
    "High frequency": "#d7191c",
}
HOTSPOT_COLOURS = {
    "Good access": "#2ca25f",
    "Moderate access": "#fee08b",
    "Poor access": "#f46d43",
    "Potential transit gap": "#a50026",
}


def _frequency_categories(departures: pd.Series) -> pd.Series:
    """Classify stops relative to the feed's non-zero departure distribution."""
    positive = departures[departures > 0]
    if positive.empty:
        return pd.Series("Low frequency", index=departures.index)

    low_cutoff, high_cutoff = positive.quantile([1 / 3, 2 / 3])
    return pd.Series(
        np.select(
            [departures <= low_cutoff, departures <= high_cutoff],
            ["Low frequency", "Medium frequency"],
            default="High frequency",
        ),
        index=departures.index,
    )


def _popup(row: object) -> folium.Popup:
    name = escape(str(row.stop_name))
    stop_id = escape(str(row.stop_id))
    content = (
        f"<b>{name}</b><br>Stop ID: {stop_id}<br>"
        f"Frequency: {row.frequency_category}<br>"
        f"Scheduled departures: {row.departures:,}<br>Distinct trips: {row.trips:,}"
    )
    return folium.Popup(content, max_width=280)


def _add_legend(transit_map: folium.Map) -> None:
    items = "".join(
        f'<div><span style="background:{colour}"></span>{label}</div>'
        for label, colour in FREQUENCY_COLOURS.items()
    )
    transit_map.get_root().html.add_child(
        Element(
            """
            <style>
              .frequency-legend {position:fixed; right:12px; bottom:24px; z-index:9999;
                background:rgba(255,255,255,.94); padding:7px 9px; border:1px solid #ccc;
                border-radius:4px; box-shadow:0 1px 4px rgba(0,0,0,.18);
                font:11px/1.5 Arial,sans-serif; color:#333;}
              .frequency-legend strong {display:block; margin-bottom:3px; font-size:12px;}
              .frequency-legend span {display:inline-block; width:8px; height:8px;
                margin-right:6px; border-radius:50%;}
            </style>
            """
            f'<div class="frequency-legend"><strong>Service frequency</strong>{items}</div>'
        )
    )
    hotspot_items = "".join(
        f'<div><span style="background:{colour};border-radius:0"></span>{label}</div>'
        for label, colour in HOTSPOT_COLOURS.items()
    )
    transit_map.get_root().html.add_child(Element(
        '<div class="frequency-legend" style="bottom:122px">'
        f'<strong>Transit gap score</strong>{hotspot_items}'
        '<small>Higher score = weaker access</small></div>'
    ))


def make_map(
    stops: gpd.GeoDataFrame,
    catchments: gpd.GeoDataFrame,
    frequency: pd.DataFrame,
    hotspots: gpd.GeoDataFrame | None = None,
) -> folium.Map:
    """Create the interactive map, with only clusters and heatmap on initially."""
    stops = stops.copy()
    frequency = frequency.copy()
    stops["stop_id"] = stops["stop_id"].astype("string")
    frequency["stop_id"] = frequency["stop_id"].astype("string")
    stops = stops.merge(frequency, on="stop_id", how="left")
    stops[["departures", "trips"]] = stops[["departures", "trips"]].fillna(0).astype(int)
    stops["frequency_category"] = _frequency_categories(stops["departures"])

    transit_map = folium.Map(
        location=DUBLIN_CENTRE,
        zoom_start=11,
        tiles="CartoDB positron",
        control_scale=True,
        prefer_canvas=True,
    )

    radius = (
        int(catchments["catchment_m"].iloc[0])
        if "catchment_m" in catchments and not catchments.empty
        else 500
    )
    catchment_layer = folium.FeatureGroup(name=f"{radius}m catchments", show=False)
    folium.GeoJson(
        catchments,
        style_function=lambda _: {
            "fillColor": "#6baed6",
            "color": "#6baed6",
            "weight": 0,
            "fillOpacity": 0.035,
        },
    ).add_to(catchment_layer)
    catchment_layer.add_to(transit_map)

    if hotspots is not None and not hotspots.empty:
        worst = hotspots.nsmallest(100, "rank")
        worst_layer = folium.FeatureGroup(name="Top 100 transit gaps", show=True)
        folium.GeoJson(
            worst,
            style_function=lambda _: {
                "fillColor": HOTSPOT_COLOURS["Potential transit gap"],
                "color": HOTSPOT_COLOURS["Potential transit gap"],
                "weight": 0.7,
                "fillOpacity": 0.3,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["rank", "cell_id", "gap_score", "nearest_stop_m", "nearby_departures"],
                aliases=["Rank", "Cell", "Gap score", "Nearest stop (m)", "Departures within 800m"],
                localize=True,
            ),
        ).add_to(worst_layer)
        worst_layer.add_to(transit_map)

        for label in HOTSPOT_COLOURS:
            subset = hotspots[hotspots["access_class"] == label]
            layer = folium.FeatureGroup(
                name=f"All cells: {label}", show=False
            )
            folium.GeoJson(
                subset,
                style_function=lambda _, colour=HOTSPOT_COLOURS[label]: {
                    "fillColor": colour, "color": colour, "weight": 0.6, "fillOpacity": 0.28,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["cell_id", "access_class", "gap_score", "nearest_stop_m", "nearby_departures"],
                    aliases=["Cell", "Access", "Gap score", "Nearest stop (m)", "Departures within 800m"],
                    localize=True,
                ),
            ).add_to(layer)
            layer.add_to(transit_map)

    heat_layer = folium.FeatureGroup(name="Frequency heatmap", show=True)
    maximum = max(1.0, float(np.log1p(stops["departures"]).max()))
    heat_data = [
        [row.geometry.y, row.geometry.x, np.log1p(row.departures) / maximum]
        for row in stops.itertuples()
        if row.geometry is not None and not row.geometry.is_empty and row.departures > 0
    ]
    HeatMap(
        heat_data,
        radius=18,
        blur=14,
        min_opacity=0.2,
        max_zoom=15,
        gradient={0.25: "#2c7bb6", 0.55: "#ffffbf", 1.0: "#d7191c"},
    ).add_to(heat_layer)
    heat_layer.add_to(transit_map)

    cluster_layer = folium.FeatureGroup(name="Stop clusters", show=True)
    clusters = MarkerCluster(
        options={"showCoverageOnHover": False, "maxClusterRadius": 45},
    ).add_to(cluster_layer)
    individual_layer = folium.FeatureGroup(name="Individual stops", show=False)

    for row in stops.itertuples():
        if row.geometry is None or row.geometry.is_empty:
            continue
        location = [row.geometry.y, row.geometry.x]
        colour = FREQUENCY_COLOURS[row.frequency_category]
        marker_options = {
            "location": location,
            "radius": 2.5,
            "color": colour,
            "fill": True,
            "fill_color": colour,
            "fill_opacity": 0.75,
            "weight": 0.5,
            "tooltip": escape(str(row.stop_name)),
        }
        folium.CircleMarker(**marker_options, popup=_popup(row)).add_to(clusters)
        folium.CircleMarker(**marker_options, popup=_popup(row)).add_to(individual_layer)

    cluster_layer.add_to(transit_map)
    individual_layer.add_to(transit_map)
    _add_legend(transit_map)
    folium.LayerControl(collapsed=True, position="topright").add_to(transit_map)
    return transit_map


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stops", default="data/processed/stops.geojson")
    parser.add_argument("--catchments", default="data/processed/stop_catchments.geojson")
    parser.add_argument("--frequency", default="data/processed/stop_frequency.csv")
    parser.add_argument("--output", default="outputs/dublin_transit_map.html")
    parser.add_argument("--hotspots", default="outputs/underserved_hotspots.geojson")
    args = parser.parse_args()
    hotspot_path = Path(args.hotspots)
    transit_map = make_map(
        gpd.read_file(args.stops),
        gpd.read_file(args.catchments),
        pd.read_csv(args.frequency, dtype={"stop_id": "string"}),
        gpd.read_file(hotspot_path) if hotspot_path.exists() else None,
    )
    output = ensure_parent(args.output)
    transit_map.save(output)
    print(f"Saved interactive map to {output}")


if __name__ == "__main__":
    main()
