"""Collect hourly weather for every Manhattan and Queens taxi zone from Open-Meteo.

API docs: https://open-meteo.com/en/docs/historical-forecast-api

Each zone is sent to the API as its centroid (latitude, longitude). Open-Meteo
accepts several coordinates in one request and returns one result per
coordinate, in the same order. Times are requested in America/New_York so they
line up with the (naive, local) TLC timestamps.

Rain, snowfall and precipitation probability are returned for the preceding
hour, so they are shifted back one hour: after this script, the row for 07:00
holds the apparent temperature at 07:00 and the rain/snow/probability for
07:00-08:00. One extra day is requested so the last hour of the period can be
filled.

The free API allows 600 "calls" per minute, and one location for six months
counts as about 13 calls. Requests are therefore sent in batches of 10 zones
with a pause between them (138 zones = 14 requests, about 5 minutes).

Output: data/processed/weather_hourly_by_zone.parquet
"""
import time

import pandas as pd

import config
from utils import get_with_retry, log, setup_logging

LOCATIONS_PER_REQUEST = 10
PAUSE_BETWEEN_REQUESTS = 15  # seconds, keeps us under the per-minute limit


def fetch_weather(zones):
    """Request hourly weather for a batch of zones. Returns one long DataFrame."""
    params = {
        "latitude": ",".join(zones["latitude"].astype(str)),
        "longitude": ",".join(zones["longitude"].astype(str)),
        "start_date": config.START_DATE,
        "end_date": str((pd.Timestamp(config.END_DATE) + pd.Timedelta(days=1)).date()),
        "hourly": ",".join(config.WEATHER_VARIABLES),
        "timezone": config.TIMEZONE,
    }
    response = get_with_retry(config.WEATHER_URL, params=params)
    results = response.json()
    if isinstance(results, dict):  # a single location comes back as an object
        results = [results]
    if len(results) != len(zones):
        raise ValueError(f"Expected {len(zones)} locations, got {len(results)}")

    frames = []
    for zone_id, result in zip(zones["LocationID"], results):
        hourly = pd.DataFrame(result["hourly"])
        hourly.insert(0, "LocationID", int(zone_id))
        hourly["grid_latitude"] = result["latitude"]
        hourly["grid_longitude"] = result["longitude"]
        hourly["grid_elevation_m"] = result["elevation"]
        frames.append(hourly)
    return frames


def align_to_hour_start(weather):
    """Shift preceding-hour variables so each row covers [hour, hour + 1)."""
    weather = weather.sort_values(["LocationID", "weather_hour"]).reset_index(drop=True)
    cols = config.PRECEDING_HOUR_VARIABLES
    weather[cols] = weather.groupby("LocationID")[cols].shift(-1)
    weather["precipitation_probability"] = weather["precipitation_probability"].round().astype("Int64")
    last_hour = pd.Timestamp(f"{config.END_DATE} 23:00")
    return weather[weather["weather_hour"] <= last_hour].reset_index(drop=True)


def check_weather(weather, zones):
    """Every zone should have one row per hour of the study period, with no gaps."""
    expected_hours = pd.date_range(config.START_DATE, f"{config.END_DATE} 23:00", freq="h")
    per_zone = weather.groupby("LocationID")["weather_hour"].agg(["count", "nunique"])
    if set(per_zone.index) != set(zones["LocationID"]):
        raise ValueError("Weather is missing for some zones")
    if (per_zone["count"] != len(expected_hours)).any() or (per_zone["nunique"] != len(expected_hours)).any():
        raise ValueError(f"Expected {len(expected_hours)} unique hours per zone:\n{per_zone}")

    nulls = weather[config.WEATHER_VARIABLES].isna().sum()
    if nulls.any():
        log.warning("Missing weather values:\n%s", nulls[nulls > 0].to_string())
    log.info("Weather check passed: %d zones x %d hours", len(per_zone), len(expected_hours))


def main():
    setup_logging()
    zones = pd.read_csv(config.ZONES_FILE)

    frames = []
    for start in range(0, len(zones), LOCATIONS_PER_REQUEST):
        if start:
            time.sleep(PAUSE_BETWEEN_REQUESTS)
        batch = zones.iloc[start:start + LOCATIONS_PER_REQUEST]
        log.info("Requesting weather for zones %s", batch["LocationID"].tolist())
        frames.extend(fetch_weather(batch))

    weather = pd.concat(frames, ignore_index=True)
    weather = weather.rename(columns={"time": "weather_hour"})
    weather["weather_hour"] = pd.to_datetime(weather["weather_hour"])
    weather = align_to_hour_start(weather)
    check_weather(weather, zones)

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    weather.to_parquet(config.WEATHER_FILE, index=False)
    log.info("Saved %d hourly rows for %d zones to %s",
             len(weather), weather["LocationID"].nunique(), config.WEATHER_FILE)


if __name__ == "__main__":
    main()
