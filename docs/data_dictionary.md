# Data Dictionary

This file describes the datasets produced by the collection pipeline and every field in them, and explains why these fields were chosen out of everything the TLC and Open-Meteo sources provide. How the data was collected is in [data_collection.md](data_collection.md).

## 1. Main dataset

**File:** `data/processed/staten_island_taxi_weather_2025-09_2026-02.csv` (same content in `.parquet`)

| Property | Value |
|---|---|
| Grain | **One row per taxi trip** |
| Rows | 2,637 (2,616 yellow, 21 green) |
| Columns | 14 |
| Area | Trips **picked up** in Staten Island (20 TLC taxi zones) |
| Period | Pickups from 2025-09-01 00:00 to 2026-02-28 23:59, local NYC time |
| Sources | NYC TLC Trip Record Data (yellow + green), TLC Taxi Zones, Open-Meteo Historical Forecast API |
| Join | Weather is matched to each trip on **pickup zone + pickup hour** |
| Missing values | None |
| Size | 0.35 MB (CSV), 0.10 MB (Parquet) |

### Field descriptions

| # | Field | Type | Unit / format | Source | Description | Purpose in the project |
|---|---|---|---|---|---|---|
| 1 | `trip_id` | integer | 1 … 2637 | generated | Sequential row ID, ordered by pickup time | Unique key for referencing a trip in later steps (cleaning logs, joins) |
| 2 | `taxi_type` | text | `yellow` / `green` | generated from the file name | Which TLC fleet the trip came from | Lets yellow and green trips share one table and be analysed together or separately |
| 3 | `pickup_datetime` | datetime | `YYYY-MM-DD HH:MM:SS`, local NYC time | TLC `tpep_pickup_datetime` (yellow) / `lpep_pickup_datetime` (green) | When the meter was engaged, i.e. when the passenger was picked up | **Defines when demand happened.** Used to build the hourly demand target and the time features (hour, weekday, month, weekend), and to match weather |
| 4 | `dropoff_datetime` | datetime | `YYYY-MM-DD HH:MM:SS`, local NYC time | TLC `tpep_dropoff_datetime` / `lpep_dropoff_datetime` | When the meter was disengaged | Gives trip duration, which is needed to spot bad records (dropoff before pickup, trips of many hours), and shows when the cab becomes free again |
| 5 | `PULocationID` | integer | TLC zone ID (1–265) | TLC | Taxi zone where the trip started. Always one of the 20 Staten Island zones here | **Defines where demand happened.** It is the spatial unit of the forecast (Zone × Hour), the key used to find the zone's coordinates and weather, and the field used to filter to Staten Island |
| 6 | `DOLocationID` | integer | TLC zone ID (1–265) | TLC | Taxi zone where the trip ended. Can be in any borough | Shows where Staten Island riders go (for example 1,304 to Brooklyn and 740 within Staten Island), and so where cabs end up after the trip, which matters for fleet positioning |
| 7 | `pickup_zone` | text | zone name | TLC zone lookup | Name of the pickup zone, e.g. *Stapleton* | Readable label for EDA, charts and the dashboard |
| 8 | `pickup_zone_latitude` | float | decimal degrees (WGS84) | computed from the TLC zone shapefile | Latitude of the pickup zone's centroid | The point sent to Open-Meteo for this zone's weather. Also usable for maps |
| 9 | `pickup_zone_longitude` | float | decimal degrees (WGS84) | computed from the TLC zone shapefile | Longitude of the pickup zone's centroid | Same as above |
| 10 | `pickup_hour` | datetime | `YYYY-MM-DD HH:00:00`, local NYC time | `pickup_datetime` rounded down to the hour | The clock hour the trip started in | **Join key with the weather table**, and the time key for the Zone × Hour demand table |
| 11 | `apparent_temperature` | float | °C, at the start of `pickup_hour` | Open-Meteo | "Feels-like" temperature at 2 m for that zone at the start of the hour. Combines air temperature, humidity and wind (wind chill / heat index) | Weather feature for comfort. Range at pickup: −24.9 to 32.2 °C |
| 12 | `rain` | float | mm, total for `pickup_hour` → +1 h | Open-Meteo | Liquid rain from large-scale weather systems during the pickup hour. Does not include convective showers or snow | Weather feature for wet conditions. 129 trips started in an hour with rain |
| 13 | `snowfall` | float | cm, total for `pickup_hour` → +1 h | Open-Meteo | Snowfall during the pickup hour | Weather feature for snow. 56 trips started in an hour with snowfall |
| 14 | `precipitation_probability` | integer | %, 0–100, for `pickup_hour` → +1 h | Open-Meteo | Model probability of more than 0.1 mm of precipitation during the pickup hour | Captures how likely wet weather looked in the forecast, which people use to plan trips in advance |

Notes:
- All timestamps are **naive local New York time** (no UTC offset). TLC publishes them this way, and the weather was requested with `timezone=America/New_York`, so both use the same clock.
- `pickup_zone_latitude` / `longitude` describe the **zone** (its centroid), not the exact pickup point. TLC stopped publishing exact coordinates in 2016 for privacy. Only zone IDs are available.
- Open-Meteo labels rain, snowfall and precipitation probability with the **end** of the hour they cover. The pipeline shifts them back one hour, so in this dataset all four weather fields refer to the pickup hour (see Step 3 in `data_collection.md`).
- Weather values are what Open-Meteo reports for the model grid cell nearest to the zone centroid. The 20 zones fall into 13 grid cells, so some neighbouring zones share the same weather values.

### Staten Island zone IDs

| ID | Zone | ID | Zone |
|---:|---|---:|---|
| 5 | Arden Heights | 156 | Mariners Harbor |
| 6 | Arrochar/Fort Wadsworth | 172 | New Dorp/Midland Beach |
| 23 | Bloomfield/Emerson Hill | 176 | Oakwood |
| 44 | Charleston/Tottenville | 187 | Port Richmond |
| 84 | Eltingville/Annadale/Prince's Bay | 204 | Rossville/Woodrow |
| 99 | Freshkills Park | 206 | Saint George/New Brighton |
| 109 | Great Kills | 214 | South Beach/Dongan Hills |
| 110 | Great Kills Park | 221 | Stapleton |
| 115 | Grymes Hill/Clifton | 245 | West Brighton |
| 118 | Heartland Village/Todt Hill | 251 | Westerleigh |

## 2. Supporting datasets

### `data/processed/weather_hourly_by_zone.csv`

Hourly weather for **every** Staten Island zone and **every** hour of the study period, including hours with no trips. It is used to add weather to zero-demand hours when building the Zone × Hour table. 86,880 rows = 20 zones × 4,344 hours.

| Field | Type | Unit | Description |
|---|---|---|---|
| `LocationID` | integer | | TLC zone ID (join with `PULocationID`) |
| `weather_hour` | datetime | local NYC time | Start of the hour |
| `apparent_temperature` | float | °C | As above. Full range −25.4 to 36.4 |
| `rain` | float | mm | As above. Rain in 5.2% of zone-hours |
| `snowfall` | float | cm | As above. Snow in 2.2% of zone-hours |
| `precipitation_probability` | integer | % | As above |
| `grid_latitude` | float | degrees | Latitude of the Open-Meteo grid cell actually used |
| `grid_longitude` | float | degrees | Longitude of the grid cell actually used |
| `grid_elevation_m` | float | metres | Elevation of the grid cell used by the API |

### `data/external/staten_island_zones.csv`

| Field | Type | Description |
|---|---|---|
| `LocationID` | integer | TLC zone ID |
| `Borough` | text | Always `Staten Island` |
| `Zone` | text | Zone name |
| `service_zone` | text | TLC service area. `Boro Zone` for all Staten Island zones |
| `latitude` | float | Zone centroid latitude (WGS84) |
| `longitude` | float | Zone centroid longitude (WGS84) |

### `data/processed/taxi_collection_summary.csv`

One row per downloaded TLC file, as an audit trail: `taxi_type`, `month`, `source_url`, `file_size_mb`, `rows_in_file`, `borough_pickups`, `outside_period_dropped`, `rows_kept`.

## 3. Why these fields were chosen

The project predicts **how many taxis are needed, where, and when**, and asks how weather changes that. The target is the number of pickups per zone per hour. A field was kept only if it helps measure that target or explain it. The field list was set in the project instructions. The reasoning behind each choice is below.

### 3.1 Taxi fields

The TLC files have 20 columns (yellow) and 21 columns (green). We kept 4.

| TLC field | Kept? | Reason |
|---|---|---|
| `tpep/lpep_pickup_datetime` | ✅ | The **when** of demand. Without it there is no hourly demand and no way to match weather |
| `tpep/lpep_dropoff_datetime` | ✅ | Gives trip duration, used to check records and to see when a cab is free again |
| `PULocationID` | ✅ | The **where** of demand. Needed for the Staten Island filter, the zone-level forecast and the weather lookup |
| `DOLocationID` | ✅ | Where trips end, i.e. where cabs end up. Supports fleet repositioning analysis |
| `VendorID` | ❌ | Which technology provider recorded the trip. Administrative only, no effect on demand |
| `passenger_count` | ❌ | We forecast **trips (cabs needed)**, not people. The field is also driver-entered and often 0 or missing |
| `trip_distance` | ❌ | Describes the trip once it happens. Does not measure or explain how many trips are requested |
| `RatecodeID` | ❌ | Tariff type (standard, JFK, Newark…). A pricing detail, not demand |
| `store_and_fwd_flag` | ❌ | Whether the record was buffered in the vehicle before upload. Technical only |
| `payment_type` | ❌ | Cash/card. Known only after the trip, not related to how much demand there is |
| `fare_amount`, `extra`, `mta_tax`, `tip_amount`, `tolls_amount`, `improvement_surcharge`, `total_amount` | ❌ | Revenue fields. The project is about demand volume, not revenue |
| `congestion_surcharge`, `cbd_congestion_fee` | ❌ | Manhattan congestion charges. They do not apply to Staten Island pickups |
| `Airport_fee` (yellow) | ❌ | Charged only at LaGuardia and JFK. Staten Island has no airport zone |
| `ehail_fee` (green) | ❌ | Unused by TLC (empty) |
| `trip_type` (green) | ❌ | Street-hail vs dispatch. Only exists for green taxis, so it cannot be compared across both fleets |

With only these four fields, yellow and green files have the **same schema** after renaming the timestamps, so they can be stacked without handling fleet-specific columns.

### 3.2 Why both yellow and green taxis

Yellow cabs can pick up anywhere in NYC. Green (Boro) cabs are only allowed to pick up street hails outside central Manhattan and the airports, which includes Staten Island. Together they make up all TLC street-hail taxi supply in the borough. Staten Island demand is very low (2,616 yellow and 21 green pickups in six months), so leaving out either fleet would lose part of an already small signal. The `taxi_type` column keeps them separable.

### 3.3 Weather fields

The Open-Meteo Historical Forecast API offers over 50 hourly variables. We kept 4.

| Open-Meteo variable | Kept? | Reason |
|---|---|---|
| `apparent_temperature` | ✅ | How cold or hot it **feels**, which is what makes people choose a cab over walking or waiting for a bus. It already includes the effect of wind and humidity, so one field replaces three |
| `rain` | ✅ | Rain is the classic driver of taxi demand: people avoid walking and waiting at stops in the rain. Kept separate from snow because the effect is different |
| `snowfall` | ✅ | Snow raises demand but also slows traffic and reduces supply, which is a different effect from rain. The study period covers winter 2025–26, so snow events are included |
| `precipitation_probability` | ✅ | The chance of rain or snow **in the forecast**. People plan around the forecast, and a dispatcher planning a day ahead only has a forecast. This variable exists in the Historical Forecast API but not in the reanalysis archive, which is one reason that API was chosen |
| `temperature_2m` | ❌ | Covered by `apparent_temperature`, which is closer to how people feel. Using both would give two highly correlated features |
| `relative_humidity_2m`, `dew_point_2m` | ❌ | Their effect on comfort is already included in `apparent_temperature` |
| `wind_speed_10m`, `wind_gusts_10m`, `wind_direction_10m` | ❌ | Wind chill is already included in `apparent_temperature`. Direction has no clear link to demand |
| `precipitation` | ❌ | Equals rain + showers + snowfall. It would repeat `rain` and `snowfall` and mix two effects we want to keep apart |
| `showers` | ❌ (not in the instructions) | Convective rain. Could be added later if short summer downpours matter (see limitations in `data_collection.md`) |
| `snow_depth` | ❌ | Snow already on the ground. Affects roads more than the decision to hail a cab, and is strongly tied to recent `snowfall` |
| `weather_code` | ❌ | A category code (clear, fog, drizzle, thunderstorm…) that is a summary of the numeric variables we already have |
| `cloud_cover*`, `visibility`, radiation, `sunshine_duration`, `uv_index` | ❌ | Little expected effect on taxi use once rain, snow and temperature are known |
| `pressure_msl`, `surface_pressure`, `cape`, soil variables, upper-level variables | ❌ | Meteorological inputs, not conditions people react to |

Together the four chosen variables describe the weather conditions riders react to (how it feels, whether it is raining or snowing) and what the forecast said. They also avoid the redundancy of the full variable list.

### 3.4 Derived fields

| Field | Why it was added |
|---|---|
| `taxi_type` | Needed once yellow and green are combined |
| `pickup_zone` | Human-readable zone name for analysis and the dashboard |
| `pickup_zone_latitude`, `pickup_zone_longitude` | Records which point the weather was taken for. The instructions ask for weather by zone latitude/longitude |
| `pickup_hour` | The exact key used to match weather, and the time unit of the demand target |
| `trip_id` | Stable row key |
