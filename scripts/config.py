"""Settings shared by all data collection scripts."""
from pathlib import Path

# Folders
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR = DATA_DIR / "external"

# Scope
BOROUGH = "Staten Island"
TAXI_TYPES = ["yellow", "green"]
MONTHS = ["2025-09", "2025-10", "2025-11", "2025-12", "2026-01", "2026-02"]
START_DATE = "2025-09-01"  # inclusive
END_DATE = "2026-02-28"  # inclusive
TIMEZONE = "America/New_York"  # TLC timestamps are naive local NYC time

# NYC TLC trip record data (https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
TLC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net"
TRIP_URL = TLC_BASE_URL + "/trip-data/{taxi_type}_tripdata_{month}.parquet"
ZONE_LOOKUP_URL = TLC_BASE_URL + "/misc/taxi_zone_lookup.csv"
ZONE_SHAPES_URL = TLC_BASE_URL + "/misc/taxi_zones.zip"

# Yellow cabs use a "tpep_" prefix and green cabs "lpep_" for the timestamps
TIMESTAMP_COLUMNS = {
    "yellow": ("tpep_pickup_datetime", "tpep_dropoff_datetime"),
    "green": ("lpep_pickup_datetime", "lpep_dropoff_datetime"),
}
TRIP_COLUMNS = ["pickup_datetime", "dropoff_datetime", "PULocationID", "DOLocationID"]

# Open-Meteo Historical Forecast API (https://open-meteo.com/en/docs/historical-forecast-api)
WEATHER_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
WEATHER_VARIABLES = [
    "apparent_temperature",
    "rain",
    "snowfall",
    "precipitation_probability",
]

# Output files
ZONES_FILE = EXTERNAL_DIR / "staten_island_zones.csv"
TRIPS_FILE = INTERIM_DIR / "taxi_trips_staten_island.parquet"
WEATHER_FILE = INTERIM_DIR / "weather_hourly_by_zone.parquet"
TAXI_SUMMARY_FILE = PROCESSED_DIR / "taxi_collection_summary.csv"
DATASET_NAME = "staten_island_taxi_weather_2025-09_2026-02"
