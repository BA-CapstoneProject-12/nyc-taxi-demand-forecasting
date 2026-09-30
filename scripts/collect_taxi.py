"""Collect yellow and green taxi trips that start in Staten Island.

Files come from the TLC trip record data page:
https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

For every month and taxi type we download the official Parquet file, keep only
the four columns we need, rename the timestamps to a common name and keep the
trips whose pickup zone (PULocationID) is in Staten Island.

Output: data/interim/taxi_trips_staten_island.parquet
"""
import pandas as pd
import pyarrow.parquet as pq

import config
from utils import download_file, log, setup_logging


def download_month(taxi_type, month):
    url = config.TRIP_URL.format(taxi_type=taxi_type, month=month)
    dest = config.RAW_DIR / "trips" / f"{taxi_type}_tripdata_{month}.parquet"
    return download_file(url, dest)


def read_borough_trips(path, taxi_type, zone_ids):
    """Read the pickup/dropoff columns for trips picked up in the given zones."""
    pickup_col, dropoff_col = config.TIMESTAMP_COLUMNS[taxi_type]
    trips = pd.read_parquet(
        path,
        columns=[pickup_col, dropoff_col, "PULocationID", "DOLocationID"],
        filters=[("PULocationID", "in", zone_ids)],
    )
    trips = trips.rename(columns={pickup_col: "pickup_datetime", dropoff_col: "dropoff_datetime"})
    trips.insert(0, "taxi_type", taxi_type)
    return trips


def in_study_period(trips):
    """TLC files sometimes contain a few trips from other months (meter clock
    errors). We have no weather for those, so keep only the study period."""
    start = pd.Timestamp(config.START_DATE)
    end = pd.Timestamp(config.END_DATE) + pd.Timedelta(days=1)
    return trips["pickup_datetime"].ge(start) & trips["pickup_datetime"].lt(end)


def main():
    setup_logging()
    zones = pd.read_csv(config.ZONES_FILE)
    zone_ids = zones["LocationID"].astype(int).tolist()

    frames, summary = [], []
    for taxi_type in config.TAXI_TYPES:
        for month in config.MONTHS:
            path = download_month(taxi_type, month)
            trips = read_borough_trips(path, taxi_type, zone_ids)
            keep = in_study_period(trips)
            total_rows = pq.read_metadata(path).num_rows
            log.info("%s %s: %d of %d trips start in %s (%d outside study period dropped)",
                     taxi_type, month, len(trips), total_rows, config.BOROUGH, (~keep).sum())
            summary.append({
                "taxi_type": taxi_type,
                "month": month,
                "source_url": config.TRIP_URL.format(taxi_type=taxi_type, month=month),
                "file_size_mb": round(path.stat().st_size / 1e6, 1),
                "rows_in_file": total_rows,
                "borough_pickups": len(trips),
                "outside_period_dropped": int((~keep).sum()),
                "rows_kept": int(keep.sum()),
            })
            frames.append(trips[keep])

    trips = pd.concat(frames, ignore_index=True)
    trips = trips.sort_values(["pickup_datetime", "taxi_type"]).reset_index(drop=True)

    config.INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    trips.to_parquet(config.TRIPS_FILE, index=False)
    log.info("Saved %d trips to %s", len(trips), config.TRIPS_FILE)

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary).to_csv(config.TAXI_SUMMARY_FILE, index=False)
    log.info("Collection summary saved to %s", config.TAXI_SUMMARY_FILE)


if __name__ == "__main__":
    main()
