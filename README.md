# nyc-taxi-demand-forecasting
NYC taxi demand forecasting using historical Yellow Taxi trips and weather data, with machine learning, time-series forecasting, association rule mining, feature engineering, and an interactive dashboard for demand insights and fleet planning.

## Data collection

Scope: **Manhattan + Queens** (138 taxi zones), **yellow + green taxis**, **Sep 2025 – Feb 2026**, with hourly weather for each taxi zone.

| Source | Used for |
|---|---|
| [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) | Trip pickup/dropoff times and zones, taxi zone lookup and boundaries |
| [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) | Hourly apparent temperature, rain, snowfall, precipitation probability per zone |

Final dataset: **23,318,979 trips**, each with its pickup/dropoff time, pickup/dropoff zone and the weather at its pickup zone and hour. It is saved as 12 monthly Parquet files in `data/interim/trips_with_weather/` (about 345 MB). The files are not in git because of their size, and the pipeline below rebuilds them. The hourly weather for every zone is in [`data/processed/weather_hourly_by_zone.parquet`](data/processed/weather_hourly_by_zone.parquet).

- [docs/data_collection.md](docs/data_collection.md): sources, collection steps, output files, dataset summary and known issues
- [docs/data_dictionary.md](docs/data_dictionary.md): every field, its purpose, and why these fields were chosen

### Reproduce

```bash
pip install -r requirements.txt
python scripts/run_pipeline.py      # downloads ~425 MB of TLC files, about 10 minutes
python scripts/profile_dataset.py   # prints the summary numbers used in the docs
```

```python
import pandas as pd
nov = pd.read_parquet("data/interim/trips_with_weather/yellow_2025-11.parquet")  # one month
```

## Project structure

```
data/
  external/    taxi_zones_manhattan_queens.csv (zones + centroid lat/lon)
  processed/   hourly weather per zone, collection summary
  raw/         downloaded TLC files (not in git)
  interim/     trips, and trips with weather, one file per month (not in git)
docs/
  data_collection.md
  data_dictionary.md
scripts/
  config.py            study period, boroughs, URLs, weather variables
  utils.py             logging and HTTP helpers
  collect_zones.py     step 1 - zones and centroid coordinates
  collect_weather.py   step 2 - hourly weather per zone
  collect_taxi.py      step 3 - TLC trips picked up in Manhattan and Queens
  build_dataset.py     step 4 - every trip with its pickup weather
  run_pipeline.py      runs steps 1-4
  profile_dataset.py   dataset profile
```
