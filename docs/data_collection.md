# Data Collection

This document describes how the raw data for the project was collected: which sources were used, how each API was called, how the taxi trips were combined with weather, and what the final dataset looks like. Field-level descriptions and the reasons for choosing each field are in [data_dictionary.md](data_dictionary.md).

## 1. Scope

The scope below was given in the project instructions.

| Item | Value |
|---|---|
| Area | **Staten Island** borough only (20 TLC taxi zones) |
| Taxi types | **Yellow** and **Green** taxis |
| Period | **1 Sep 2025 00:00 to 28 Feb 2026 23:59** (6 months, 181 days), local NYC time |
| Taxi fields | Pickup time, dropoff time, `PULocationID`, `DOLocationID` |
| Weather fields | Hourly apparent temperature, rain, snowfall, precipitation probability |
| Weather location | One point per taxi zone (the zone's centroid latitude/longitude) |

A trip counts as Staten Island demand when it is **picked up** in a Staten Island zone (`PULocationID` in the 20 Staten Island zones). The drop-off can be anywhere. We filter on the pickup because the project forecasts where passengers need a cab, and the weather joined to a trip is the weather the passenger faced when they got in.

## 2. Data sources

| # | Data | Provider | Access method | Endpoint |
|---|---|---|---|---|
| 1 | Yellow taxi trip records | NYC Taxi & Limousine Commission (TLC) | HTTP download of the official monthly Parquet files | `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_YYYY-MM.parquet` |
| 2 | Green taxi trip records | NYC TLC | Same as above | `https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_YYYY-MM.parquet` |
| 3 | Taxi zone lookup (ID → zone name → borough) | NYC TLC | HTTP download (CSV) | `https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv` |
| 4 | Taxi zone boundaries | NYC TLC | HTTP download (zipped shapefile) | `https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip` |
| 5 | Hourly weather | Open-Meteo | REST API (JSON) | `https://historical-forecast-api.open-meteo.com/v1/forecast` |

- TLC trip record page: <https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>
- Open-Meteo Historical Forecast API docs: <https://open-meteo.com/en/docs/historical-forecast-api>

Both sources are free and need no API key.

### Why these sources

- **TLC monthly Parquet files.** These are the official trip records linked from the TLC page. Each month has a fixed URL, so the download can be scripted and repeated, and every team member gets the same input. The same data is on NYC Open Data (Socrata API), but that API returns rows in pages, so pulling a whole month means hundreds of requests. We need about 25 million yellow rows to find the 2,616 that start in Staten Island, so downloading each file once and filtering locally is much faster and gives a fixed version of the data.
- **Open-Meteo Historical Forecast API.** It gives hourly weather for any latitude/longitude, which lets us get weather **per taxi zone** instead of using one weather station for the whole city. It is built from archived runs of high-resolution weather models, and it has `precipitation_probability`. The Historical Weather (reanalysis archive) API does not have that variable.

## 3. Collection steps

The whole process is scripted. One command runs it from start to finish:

```bash
pip install -r requirements.txt
python scripts/run_pipeline.py
```

```
 TLC zone lookup ─┐
                  ├─► Step 1: Staten Island zones + centroid lat/lon ─┬─────────────────────┐
 TLC zone shapes ─┘         (data/external/staten_island_zones.csv)   │                     │
                                                                      ▼                     ▼
 TLC monthly Parquet ─► Step 2: trips picked up in Staten Island   Step 3: Open-Meteo hourly weather
 (yellow + green,          (data/interim/taxi_trips_...parquet)       for every zone centroid
  Sep 2025 – Feb 2026)                    │                         (data/processed/weather_hourly_by_zone.csv)
                                          │                                  │
                                          └──────────► Step 4: join on (pickup zone, pickup hour) ◄──┘
                                                       (data/processed/staten_island_taxi_weather_2025-09_2026-02.csv)
```

### Step 1: Staten Island zones and their coordinates (`scripts/collect_zones.py`)

1. Download `taxi_zone_lookup.csv` (265 zones) and keep the rows where `Borough == "Staten Island"`. This gives **20 zones**.
2. Download `taxi_zones.zip`, the TLC zone boundary shapefile. The coordinates are in the NY State Plane Long Island system (**EPSG:2263**, US feet).
3. For each zone polygon, compute the **area-weighted centroid** in State Plane coordinates. Holes and multi-part zones are handled by summing the signed areas of all rings.
4. Convert the centroid to **WGS84 latitude/longitude** (EPSG:4326) with `pyproj`, since that is what Open-Meteo expects.
5. Save `data/external/staten_island_zones.csv` with `LocationID, Borough, Zone, service_zone, latitude, longitude`.

The script stops with an error if any Staten Island zone has no shape.

### Step 2: Taxi trips (`scripts/collect_taxi.py`)

For each taxi type (yellow, green) and each month (2025-09 to 2026-02), that is 12 files:

1. **Download** the monthly Parquet file into `data/raw/trips/`. Downloads are streamed to disk and retried on network errors or HTTP 429/5xx. A file that is already on disk is not downloaded again.
2. **Read only the four needed columns**, pushing the filter `PULocationID IN (20 Staten Island zone IDs)` into the Parquet reader, so the other 99.99% of rows never reach memory as a DataFrame.
3. **Standardise the column names.** Yellow files use `tpep_pickup_datetime` / `tpep_dropoff_datetime` and green files use `lpep_…`. Both are renamed to `pickup_datetime` / `dropoff_datetime`, and a `taxi_type` column is added so the two types can be stacked in one table.
4. **Keep only trips whose pickup falls in the study period.** TLC files sometimes contain a few trips from other months (meter clock errors). We would have no weather for those. In this collection no trip was dropped by this rule.
5. Stack all 12 months, sort by pickup time, and save to `data/interim/taxi_trips_staten_island.parquet`.
6. Write a per-file audit table to `data/processed/taxi_collection_summary.csv` (URL, file size, rows in file, Staten Island pickups, rows dropped, rows kept).

| Month | Yellow rows in file | Yellow SI pickups | Green rows in file | Green SI pickups |
|---|---:|---:|---:|---:|
| 2025-09 | 4,251,015 | 438 | 48,893 | 4 |
| 2025-10 | 4,428,699 | 409 | 49,416 | 0 |
| 2025-11 | 4,181,444 | 392 | 46,912 | 4 |
| 2025-12 | 4,305,006 | 462 | 48,236 | 3 |
| 2026-01 | 3,724,889 | 486 | 40,272 | 4 |
| 2026-02 | 3,399,866 | 429 | 37,373 | 6 |
| **Total** | **24,290,919** | **2,616** | **271,102** | **21** |

### Step 3: Hourly weather per zone (`scripts/collect_weather.py`)

1. Read the 20 zone centroids from Step 1.
2. Call the Open-Meteo Historical Forecast API. The API accepts several comma-separated coordinates in one request, so the 20 zones are sent in **2 requests of 10 zones each**. Parameters:

   | Parameter | Value | Why |
   |---|---|---|
   | `latitude`, `longitude` | zone centroids | weather at each zone |
   | `start_date`, `end_date` | `2025-09-01`, `2026-02-28` | study period |
   | `hourly` | `apparent_temperature,rain,snowfall,precipitation_probability` | variables from the instructions |
   | `timezone` | `America/New_York` | returns local NYC hours, the same clock as the TLC timestamps |

   Example request (one zone):
   ```
   https://historical-forecast-api.open-meteo.com/v1/forecast?latitude=40.63897&longitude=-74.10231&start_date=2025-09-01&end_date=2026-02-28&hourly=apparent_temperature,rain,snowfall,precipitation_probability&timezone=America/New_York
   ```
3. Turn each zone's response into rows of `LocationID, weather_hour, <4 variables>`. We also keep the grid-cell latitude, longitude and elevation that Open-Meteo actually used.
4. **Check completeness**: every zone must have exactly one row for each of the **4,344 hours** in the period (181 days × 24), with no missing values. The script stops with an error if not.
5. Save to `data/processed/weather_hourly_by_zone.csv` (20 × 4,344 = **86,880 rows**).

This table covers **every hour**, including hours with no taxi trips. The forecasting stage will need weather for zero-demand hours too, when it builds the Zone × Hour demand table.

### Step 4: Combine trips and weather (`scripts/build_dataset.py`)

For every trip:

1. Take the pickup zone `PULocationID`.
2. Look up the zone name and centroid latitude/longitude (Step 1). This is the location used for the weather request.
3. Round the pickup time **down to the hour**: `pickup_hour = floor(pickup_datetime, 1h)`. Open-Meteo hourly values are labelled by the start of the hour. For example, a pickup at 07:42 gets the 07:00 weather row.
4. Left-join the weather table on **(`PULocationID`, `pickup_hour`)**.
5. Add a sequential `trip_id`.

Checks run before saving:
- The row count is unchanged by the joins (each join is validated as many-to-one, so no trip can be duplicated).
- Every trip has a zone name and all four weather values. **0 trips are missing weather.**

The result is saved as CSV and Parquet:
`data/processed/staten_island_taxi_weather_2025-09_2026-02.csv` / `.parquet`.

## 4. Output files

| File | In git | Rows | Description |
|---|---|---:|---|
| `data/processed/staten_island_taxi_weather_2025-09_2026-02.csv` (+ `.parquet`) | yes | 2,637 | **Final dataset**: one row per trip with the weather at pickup |
| `data/processed/weather_hourly_by_zone.csv` | yes | 86,880 | Hourly weather for every Staten Island zone and every hour |
| `data/processed/taxi_collection_summary.csv` | yes | 12 | Audit of each downloaded TLC file |
| `data/external/staten_island_zones.csv` | yes | 20 | Staten Island zones with centroid latitude/longitude |
| `data/interim/taxi_trips_staten_island.parquet` | no | 2,637 | Filtered trips before the weather join |
| `data/raw/` | no | n/a | Downloaded TLC files (about 430 MB), rebuilt by the pipeline |

`data/raw/` and `data/interim/` are in `.gitignore`. Run `python scripts/run_pipeline.py` to rebuild them.

## 5. Dataset summary

Run `python scripts/profile_dataset.py` to reproduce these numbers.

- **2,637 trips**: 2,616 yellow (99.2%) and 21 green (0.8%).
- **Pickups from** 2025-09-01 00:24 **to** 2026-02-28 23:11.
- **About 14.6 trips per day** for the whole borough.
- **19 of the 20 zones** have at least one pickup. Great Kills Park (110) has none. The busiest zones are Arrochar/Fort Wadsworth (580), Stapleton (416), South Beach/Dongan Hills (267), Grymes Hill/Clifton (234) and Bloomfield/Emerson Hill (200).
- **Clear morning peak**: 494 pickups start between 07:00 and 07:59, the busiest hour of the day, compared with roughly 40–120 in most other hours.
- **Destinations**: Brooklyn 1,304, Staten Island 740, Manhattan 464, Queens 85, Bronx 18, Newark Airport 9, unknown 17.
- **Weather at pickup**: apparent temperature from −24.9 °C to 32.2 °C. 147 trips started during rain and 62 during snowfall.

| Month | Trips | Mean apparent temp. at pickup (°C) |
|---|---:|---:|
| 2025-09 | 442 | 20.0 |
| 2025-10 | 409 | 10.0 |
| 2025-11 | 396 | 2.5 |
| 2025-12 | 465 | −5.9 |
| 2026-01 | 490 | −9.0 |
| 2026-02 | 435 | −7.3 |

## 6. Things to know before using the data

**Timezone and daylight saving.** TLC timestamps are naive local NYC time, and weather was requested in `America/New_York`, so both use the same clock. Daylight saving ended on 2 Nov 2025, so 01:00–01:59 happened twice. TLC timestamps cannot tell the two apart, and Open-Meteo returns a single 01:00 row for that day, so trips from both 01:00 hours get the same weather. The spring-forward change (8 Mar 2026) is outside the study period.

**Weather resolution.** Weather is requested at each zone's centroid, but Open-Meteo returns the value of the nearest model grid cell. The 20 Staten Island zones map to **13 distinct grid cells**, so some neighbouring zones share identical weather. The grid cell used for each zone is kept in `weather_hourly_by_zone.csv` (`grid_latitude`, `grid_longitude`, `grid_elevation_m`).

**Centroid as the zone location.** A zone centroid stands for the whole zone. Staten Island zones are a few kilometres across, which is about the size of a weather-model grid cell, so this adds little error.

**Rain vs showers.** In Open-Meteo, `rain` is rain from large-scale weather systems and `showers` is convective rain, reported separately. `showers` was not in the requested variables, so short convective downpours (mostly in September) are not counted in `rain`. If this matters for modelling, add `showers` to `WEATHER_VARIABLES` in `scripts/config.py` and rerun.

**Low volume.** Staten Island has very little street-hail taxi activity: about 15 pickups a day for the whole borough, spread over 20 zones. Most zone-hours will have **zero** pickups. This should be taken into account in the Zone × Hour aggregation and in the choice of models. For comparison, **6,529** yellow/green trips in the same period came *into* Staten Island from other boroughs. They are not in this dataset because they were not picked up in Staten Island.

**Left for the data preparation step.** Collection only filters by borough and period. It does not remove records. The profile script reports these issues for the cleaning step:

| Issue | Trips |
|---|---:|
| Exact duplicate rows (same type, times and zones) | 26 |
| Dropoff at or before pickup | 3 |
| Trip longer than 6 hours | 5 |
| Dropoff zone Unknown / Outside NYC (264, 265) | 17 |

**Data versions.** Data was collected on **30 Sep 2026**. The TLC 2026-02 files were last modified on 25 Mar 2026. TLC occasionally republishes files, so rerunning the pipeline later could give slightly different counts. `taxi_collection_summary.csv` records the file sizes that were used.

## 7. Scripts

| Script | What it does |
|---|---|
| `scripts/config.py` | Study period, borough, taxi types, URLs, weather variables, output paths |
| `scripts/utils.py` | Logging, HTTP GET with retries, cached file download |
| `scripts/collect_zones.py` | Step 1: Staten Island zones and centroid coordinates |
| `scripts/collect_taxi.py` | Step 2: download TLC files and filter Staten Island pickups |
| `scripts/collect_weather.py` | Step 3: hourly weather per zone from Open-Meteo |
| `scripts/build_dataset.py` | Step 4: join trips with weather and save the final dataset |
| `scripts/run_pipeline.py` | Runs steps 1–4 in order |
| `scripts/profile_dataset.py` | Prints the summary numbers used in this document |
