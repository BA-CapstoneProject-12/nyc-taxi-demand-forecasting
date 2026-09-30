# nyc-taxi-demand-forecasting
NYC taxi demand forecasting using historical Yellow Taxi trips and weather data, with machine learning, time-series forecasting, association rule mining, feature engineering, and an interactive dashboard for demand insights and fleet planning.

## Data collection

Current scope: **Staten Island**, **yellow + green taxis**, **Sep 2025 – Feb 2026**, with hourly weather for each taxi zone.

| Source | Used for |
|---|---|
| [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) | Trip pickup/dropoff times and zones, taxi zone lookup and boundaries |
| [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) | Hourly apparent temperature, rain, snowfall, precipitation probability per zone |

Final dataset: [`data/processed/staten_island_taxi_weather_2025-09_2026-02.csv`](data/processed/staten_island_taxi_weather_2025-09_2026-02.csv), 2,637 trips, each with the weather for its pickup zone and hour.

- [docs/data_collection.md](docs/data_collection.md): sources, collection steps, output files, dataset summary and known issues
- [docs/data_dictionary.md](docs/data_dictionary.md): every field, its purpose, and why these fields were chosen

### Reproduce

```bash
pip install -r requirements.txt
python scripts/run_pipeline.py      # downloads ~430 MB of TLC files into data/raw/
python scripts/profile_dataset.py   # prints the summary numbers used in the docs
```

## Project structure

```
data/
  external/    staten_island_zones.csv (zones + centroid lat/lon)
  processed/   final dataset, hourly weather per zone, collection summary
  raw/         downloaded TLC files (not in git)
  interim/     filtered trips before the weather join (not in git)
docs/
  data_collection.md
  data_dictionary.md
scripts/
  config.py            study period, borough, URLs, weather variables
  utils.py             logging and HTTP helpers
  collect_zones.py     step 1 - zones and centroid coordinates
  collect_taxi.py      step 2 - TLC trips picked up in Staten Island
  collect_weather.py   step 3 - hourly weather per zone
  build_dataset.py     step 4 - join trips with weather
  run_pipeline.py      runs steps 1-4
  profile_dataset.py   dataset profile
```
