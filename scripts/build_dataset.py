"""Join every taxi trip with the weather at its pickup zone and hour.

For each trip:
  1. take the pickup zone (PULocationID),
  2. look up that zone's centroid latitude/longitude,
  3. round the pickup time down to the hour,
  4. attach the Open-Meteo weather for that zone and hour.

The trips are processed one monthly file at a time, and the output keeps the
same split (about 23 million rows in total, too big for git).

Output: data/interim/trips_with_weather/{taxi_type}_{month}.parquet
"""
import pandas as pd

import config
from utils import log, setup_logging

OUTPUT_COLUMNS = [
    "taxi_type",
    "pickup_datetime",
    "dropoff_datetime",
    "PULocationID",
    "DOLocationID",
    "pickup_borough",
    "pickup_zone",
    "pickup_zone_latitude",
    "pickup_zone_longitude",
    "pickup_hour",
    *config.WEATHER_VARIABLES,
]


def load_zones():
    zones = pd.read_csv(config.ZONES_FILE)
    zones = zones.rename(columns={
        "LocationID": "PULocationID",
        "Borough": "pickup_borough",
        "Zone": "pickup_zone",
        "latitude": "pickup_zone_latitude",
        "longitude": "pickup_zone_longitude",
    })
    zones = zones[["PULocationID", "pickup_borough", "pickup_zone",
                   "pickup_zone_latitude", "pickup_zone_longitude"]]
    for col in ("pickup_borough", "pickup_zone"):
        zones[col] = zones[col].astype("category")
    return zones


def load_weather():
    weather = pd.read_parquet(config.WEATHER_FILE)
    weather = weather.rename(columns={"LocationID": "PULocationID", "weather_hour": "pickup_hour"})
    return weather[["PULocationID", "pickup_hour", *config.WEATHER_VARIABLES]]


def add_weather(trips, zones, weather):
    data = trips.copy()
    data["pickup_hour"] = data["pickup_datetime"].dt.floor("h")
    data = data.merge(zones, on="PULocationID", how="left", validate="many_to_one")
    data = data.merge(weather, on=["PULocationID", "pickup_hour"], how="left", validate="many_to_one")
    return data[OUTPUT_COLUMNS]


def check_trips(data, trips, name):
    if len(data) != len(trips):
        raise ValueError(f"{name}: row count changed in the join ({len(trips)} -> {len(data)})")
    missing = data[config.WEATHER_VARIABLES + ["pickup_zone"]].isna().any(axis=1).sum()
    if missing:
        raise ValueError(f"{name}: {missing} trips did not get zone or weather data")


def main():
    setup_logging()
    zones = load_zones()
    weather = load_weather()
    weather["pickup_hour"] = weather["pickup_hour"].astype("datetime64[us]")

    config.TRIPS_WITH_WEATHER_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for taxi_type in config.TAXI_TYPES:
        for month in config.MONTHS:
            name = f"{taxi_type}_{month}"
            trips = pd.read_parquet(config.TRIPS_DIR / f"{name}.parquet")
            data = add_weather(trips, zones, weather)
            check_trips(data, trips, name)
            data.to_parquet(config.TRIPS_WITH_WEATHER_DIR / f"{name}.parquet", index=False)
            total += len(data)
            log.info("%s: %d trips, all with weather", name, len(data))

    log.info("Saved %d trips with weather to %s", total, config.TRIPS_WITH_WEATHER_DIR)


if __name__ == "__main__":
    main()
