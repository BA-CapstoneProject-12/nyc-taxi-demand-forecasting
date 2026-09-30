"""Collect hourly weather for every Staten Island taxi zone from Open-Meteo.

API docs: https://open-meteo.com/en/docs/historical-forecast-api

Each zone is sent to the API as its centroid (latitude, longitude). Open-Meteo
accepts several coordinates in one request and returns one result per
coordinate, in the same order. Times are requested in America/New_York so they
line up with the (naive, local) TLC timestamps.

Output: data/processed/weather_hourly_by_zone.csv
"""
import pandas as pd

import config
from utils import get_with_retry, log, setup_logging

LOCATIONS_PER_REQUEST = 10


def fetch_weather(zones):
    """Request hourly weather for a batch of zones. Returns one long DataFrame."""
    params = {
        "latitude": ",".join(zones["latitude"].astype(str)),
        "longitude": ",".join(zones["longitude"].astype(str)),
        "start_date": config.START_DATE,
        "end_date": config.END_DATE,
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


def main():
    setup_logging()
    zones = pd.read_csv(config.ZONES_FILE)

    frames = []
    for start in range(0, len(zones), LOCATIONS_PER_REQUEST):
        batch = zones.iloc[start:start + LOCATIONS_PER_REQUEST]
        log.info("Requesting weather for zones %s", batch["LocationID"].tolist())
        frames.extend(fetch_weather(batch))

    weather = pd.concat(frames, ignore_index=True)
    weather = weather.rename(columns={"time": "weather_hour"})
    weather["weather_hour"] = pd.to_datetime(weather["weather_hour"])

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    weather.to_csv(config.WEATHER_FILE, index=False)
    log.info("Saved %d hourly rows for %d zones to %s",
             len(weather), weather["LocationID"].nunique(), config.WEATHER_FILE)


if __name__ == "__main__":
    main()
