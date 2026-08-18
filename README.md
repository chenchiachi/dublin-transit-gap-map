# Dublin Transit Gap Map

Mapping underserved public transport areas in Dublin using GTFS and geospatial
analysis. The project maps existing stops, service intensity, straight-line
walking catchments, areas with poor access, and potential locations for new or
improved stops.

## Data

Put an unpacked GTFS feed in `data/raw/gtfs/`, or supply the path to a GTFS ZIP.
The feed should include `stops.txt`, `routes.txt`, `trips.txt`, `stop_times.txt`,
`calendar.txt`, `calendar_dates.txt`, and `shapes.txt` where available.

## Output

The interactive map is written to `outputs/dublin_transit_map.html`. It opens on
a clean Dublin-wide basemap with the frequency heatmap and clustered stops
visible. Its layer control can independently toggle:

- Stop clusters (on by default)
- Frequency heatmap (on by default)
- Individual frequency-coloured stops (off by default)
- 500m catchments (off by default)

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
cleaned stops, catchments, and frequency counts in `data/processed/`, then
rebuilds `outputs/dublin_transit_map.html`.

Each stage can also be run separately:

```powershell
python src/load_gtfs_stops.py --gtfs data/raw/gtfs
python src/create_catchments.py --radius 500
python src/calculate_service_frequency.py --gtfs data/raw/gtfs
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
