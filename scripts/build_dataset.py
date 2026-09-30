"""Join every Staten Island taxi trip with the weather at its pickup zone and hour.

For each trip:
  1. take the pickup zone (PULocationID),
  2. look up that zone's centroid latitude/longitude,
  3. round the pickup time down to the hour,
  4. attach the Open-Meteo weather for that zone and hour.

Output: data/processed/staten_island_taxi_weather_2025-09_2026-02.{csv,parquet}
"""
import pandas as pd

import config
from utils import log, setup_logging

OUTPUT_COLUMNS = [
    "trip_id",
    "taxi_type",
    "pickup_datetime",
    "dropoff_datetime",
    "PULocationID",
    "DOLocationID",
    "pickup_zone",
    "pickup_zone_latitude",
    "pickup_zone_longitude",
    "pickup_hour",
    *config.WEATHER_VARIABLES,
]


def build(trips, zones, weather):
    zones = zones.rename(columns={
        "LocationID": "PULocationID",
        "Zone": "pickup_zone",
        "latitude": "pickup_zone_latitude",
        "longitude": "pickup_zone_longitude",
    })[["PULocationID", "pickup_zone", "pickup_zone_latitude", "pickup_zone_longitude"]]

    weather = weather.rename(columns={"LocationID": "PULocationID", "weather_hour": "pickup_hour"})
    weather = weather[["PULocationID", "pickup_hour", *config.WEATHER_VARIABLES]]

    data = trips.copy()
    data["pickup_hour"] = data["pickup_datetime"].dt.floor("h")
    data = data.merge(zones, on="PULocationID", how="left", validate="many_to_one")
    data = data.merge(weather, on=["PULocationID", "pickup_hour"], how="left", validate="many_to_one")
    data.insert(0, "trip_id", range(1, len(data) + 1))
    return data[OUTPUT_COLUMNS]


def check_dataset(data, trips):
    if len(data) != len(trips):
        raise ValueError(f"Row count changed in the join: {len(trips)} -> {len(data)}")
    missing = data[config.WEATHER_VARIABLES + ["pickup_zone"]].isna().any(axis=1).sum()
    if missing:
        raise ValueError(f"{missing} trips did not get zone or weather data")
    log.info("Dataset check passed: %d trips, all with weather", len(data))


def main():
    setup_logging()
    trips = pd.read_parquet(config.TRIPS_FILE)
    zones = pd.read_csv(config.ZONES_FILE)
    weather = pd.read_csv(config.WEATHER_FILE, parse_dates=["weather_hour"])

    data = build(trips, zones, weather)
    check_dataset(data, trips)

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = config.PROCESSED_DIR / f"{config.DATASET_NAME}.csv"
    data.to_csv(csv_path, index=False)
    data.to_parquet(csv_path.with_suffix(".parquet"), index=False)
    log.info("Saved %s (.csv and .parquet)", csv_path.stem)


if __name__ == "__main__":
    main()
