"""Get the Staten Island taxi zones from the TLC zone lookup table.

Output: data/external/staten_island_zones.csv
"""
import pandas as pd

import config
from utils import download_file, log, setup_logging


def load_zone_lookup():
    path = download_file(config.ZONE_LOOKUP_URL, config.RAW_DIR / "taxi_zone_lookup.csv")
    return pd.read_csv(path)


def borough_zones(lookup, borough=config.BOROUGH):
    zones = lookup[lookup["Borough"] == borough].copy()
    if zones.empty:
        raise ValueError(f"No zones found for borough {borough!r}")
    return zones.sort_values("LocationID").reset_index(drop=True)


def main():
    setup_logging()
    zones = borough_zones(load_zone_lookup())
    config.EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    zones.to_csv(config.ZONES_FILE, index=False)
    log.info("%d %s zones saved to %s", len(zones), config.BOROUGH, config.ZONES_FILE)


if __name__ == "__main__":
    main()
