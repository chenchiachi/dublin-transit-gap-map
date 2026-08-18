# Dublin Transit Gap Map

Mapping underserved public transport areas in Dublin using GTFS and geospatial
analysis. The project maps existing stops, service intensity, straight-line
walking catchments, and potential locations for new or improved service.

## Data

Put an unpacked GTFS feed in `data/raw/gtfs/`, or supply the path to a GTFS ZIP.
The feed should include `stops.txt`, `routes.txt`, `trips.txt`, `stop_times.txt`,
`calendar.txt`, `calendar_dates.txt`, and `shapes.txt` where available.

## Output

The interactive map is written to `outputs/dublin_transit_map.html`. It opens on
a clean Dublin-wide basemap with the frequency heatmap and clustered stops
visible. The 100 highest-ranked cells are also visible by default as transparent
red polygons; complete layers for all access classes are available from the
layer control. Outputs also include:

- `outputs/underserved_hotspots.geojson` — the scored analysis grid
- `outputs/hotspot_ranking.csv` — all cells ranked from highest to lowest need

The map layer control can independently toggle:

- Stop clusters (on by default)
- Frequency heatmap (on by default)
- Individual frequency-coloured stops (off by default)
- 500m catchments (off by default)
- Top 100 transit gaps (on by default)
- Complete good, moderate, poor, and potential-gap classes (off by default)

Stops are grouped into low, medium, and high service-frequency categories based
on thirds of the non-zero scheduled-departure distribution. Heatmap weights use
a logarithmic scale so the busiest stops do not obscure the rest of the network.

## Run the first-pass pipeline

Install the dependencies, place an unpacked feed in `data/raw/gtfs/` (or pass a
GTFS ZIP path), and run:

```powershell
python -m pip install -r requirements.txt
python src/run_pipeline.py --gtfs data/raw/gtfs --radius 500
```

Rerun the same command whenever the GTFS feed changes. The pipeline regenerates
cleaned stops, catchments, and frequency counts in `data/processed/`; scores the
grid; writes both hotspot exports; then rebuilds the interactive map. Use
`--grid-size 500` (metres), for example, for a finer but larger analysis.

Each stage can also be run separately:

```powershell
python src/load_gtfs_stops.py --gtfs data/raw/gtfs
python src/create_catchments.py --radius 500
python src/calculate_service_frequency.py --gtfs data/raw/gtfs
python src/analyze_hotspots.py --cell-size 1000 --service-radius 800
python src/make_folium_map.py
```

To rebuild only the map from existing processed files, run:

```powershell
python src/make_folium_map.py --output outputs/dublin_transit_map.html
```

The frequency measure is deliberately simple: it counts scheduled
departures (and distinct trips) across the entire GTFS `stop_times.txt` table.
It does not yet filter by weekday, date, route, or time period. Catchments are
straight-line buffers, not walking-network isochrones.

## Underserved hotspot method

The first-pass analysis creates a regular 1 km square grid over an explicitly
defined Dublin study rectangle (`-6.55, 53.15, -6.05, 53.65`). Calculations use
Irish Transverse Mercator (EPSG:2157), so distances are in metres. For every cell
centroid it measures the straight-line distance to the nearest GTFS stop and
sums scheduled departures for every stop within 800 m.

The 0–100 transit gap score gives equal weight to two need components: distance
to a stop (capped at 1,600 m) and low nearby service. Nearby service is
log-scaled against the grid's 90th percentile so a few very busy stops do not
dominate. Scores are classified as Good access (0–25), Moderate access (>25–50),
Poor access (>50–75), or Potential transit gap (>75). This is a screening tool,
not a statement of actual demand: it uses straight-line proximity and the
feed-wide schedule count rather than walking routes or a selected service day.

Population is intentionally not used yet. The scoring code includes a
zero-weight `population_need_placeholder`; a later version can join census or
population-grid data by cell and give that component a documented weight. That
would help distinguish genuinely underserved populated areas from parks,
industrial land, rural edges, water, and other low-demand places.
