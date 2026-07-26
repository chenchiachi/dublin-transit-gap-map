# dublin-transit-gap-map

Mapping underserved public transport areas in Dublin using GTFS and geospatial analysis.



\# Dublin Transit Gap Map



This project identifies areas in Dublin where public transport stops may be most needed.



\## Goal



Create maps showing:



\- Existing transit stops from GTFS data

\- Walking catchments around stops

\- Areas with poor transit access

\- Candidate hotspots for new or improved stops



\## Data



Put GTFS files inside:



data/raw/gtfs/



Expected files:



\- stops.txt

\- routes.txt

\- trips.txt

\- stop\_times.txt

\- calendar.txt

\- calendar\_dates.txt

\- shapes.txt



\## Outputs



Generated maps and analysis files will be saved in:



outputs/

## Run the first-pass pipeline

Install the dependencies, place an unpacked feed in `data/raw/gtfs/` (or pass a
GTFS ZIP path), and run:

```powershell
python -m pip install -r requirements.txt
python src/run_pipeline.py --gtfs data/raw/gtfs --radius 500
```

The pipeline writes cleaned stops, catchments, and frequency counts to
`data/processed/`, plus the interactive map to
`outputs/dublin_transit_map.html`.

Each stage can also be run separately:

```powershell
python src/load_gtfs_stops.py --gtfs data/raw/gtfs
python src/create_catchments.py --radius 500
python src/calculate_service_frequency.py --gtfs data/raw/gtfs
python src/make_folium_map.py
```

The initial frequency measure is deliberately simple: it counts scheduled
departures (and distinct trips) across the entire GTFS `stop_times.txt` table.
It does not yet filter by weekday, date, route, or time period. Catchments are
straight-line buffers, not walking-network isochrones.
