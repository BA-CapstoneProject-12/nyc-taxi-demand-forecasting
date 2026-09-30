"""Download the monthly TLC trip record files for yellow and green taxis.

Files come from the TLC trip record data page:
https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
"""
import config
from utils import download_file, log, setup_logging


def download_month(taxi_type, month):
    url = config.TRIP_URL.format(taxi_type=taxi_type, month=month)
    dest = config.RAW_DIR / "trips" / f"{taxi_type}_tripdata_{month}.parquet"
    return download_file(url, dest)


def main():
    setup_logging()
    for taxi_type in config.TAXI_TYPES:
        for month in config.MONTHS:
            download_month(taxi_type, month)
    log.info("All trip files downloaded")


if __name__ == "__main__":
    main()
