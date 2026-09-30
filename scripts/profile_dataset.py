"""Print a profile of the collected data (numbers quoted in docs/).

    python scripts/profile_dataset.py

The trip files are read one at a time, so this runs in little memory.
"""
import pandas as pd

import config

COLUMNS = ["taxi_type", "pickup_datetime", "PULocationID", "DOLocationID",
           "pickup_borough", "pickup_zone", *config.WEATHER_VARIABLES]


def add_counts(total, counts):
    return counts if total is None else total.add(counts, fill_value=0)


def main():
    summary = pd.read_csv(config.TAXI_SUMMARY_FILE)
    zones = pd.read_csv(config.ZONES_FILE)
    weather = pd.read_parquet(config.WEATHER_FILE)
    borough_of = pd.read_csv(config.RAW_DIR / "taxi_zone_lookup.csv").set_index("LocationID")["Borough"]

    print("== Collection ==")
    print(f"rows in the 12 TLC files:          {summary['rows_in_file'].sum():,}")
    print(f"picked up in {' or '.join(config.BOROUGHS)}: {summary['borough_pickups'].sum():,}")
    print(f"outside study period (dropped):    {summary['outside_period_dropped'].sum():,}")
    print(f"trips kept:                        {summary['rows_kept'].sum():,}")

    rows = 0
    missing = by_borough = by_month = by_zone = by_hour = dropoffs = None
    first = last = None
    rain_trips = snow_trips = 0
    for file in sorted(config.TRIPS_WITH_WEATHER_DIR.glob("*.parquet")):
        trips = pd.read_parquet(file, columns=COLUMNS)
        rows += len(trips)
        missing = add_counts(missing, trips.isna().sum())
        by_borough = add_counts(by_borough, trips.groupby(["pickup_borough", "taxi_type"], observed=True).size())
        month = trips["pickup_datetime"].dt.strftime("%Y-%m")
        by_month = add_counts(by_month, trips.groupby([month, "taxi_type"], observed=True).size())
        by_zone = add_counts(by_zone, trips["PULocationID"].value_counts())
        by_hour = add_counts(by_hour, trips["pickup_datetime"].dt.hour.value_counts())
        dropoffs = add_counts(dropoffs, trips["DOLocationID"].map(borough_of).fillna("N/A").value_counts())
        rain_trips += int((trips["rain"] > 0).sum())
        snow_trips += int((trips["snowfall"] > 0).sum())
        first = min(first, trips["pickup_datetime"].min()) if first is not None else trips["pickup_datetime"].min()
        last = max(last, trips["pickup_datetime"].max()) if last is not None else trips["pickup_datetime"].max()

    print(f"\n== Trips with weather ({config.TRIPS_WITH_WEATHER_DIR.name}/) ==")
    print(f"rows: {rows:,}   columns: {len(missing)}")
    print(f"pickups from {first} to {last}")

    print("\n-- missing values --")
    print(missing.astype("int64").to_string())

    print("\n-- trips by pickup borough and taxi type --")
    print(by_borough.astype("int64").unstack(fill_value=0).to_string())

    print("\n-- trips by pickup month and taxi type --")
    print(by_month.astype("int64").unstack(fill_value=0).to_string())

    names = zones.set_index("LocationID")[["Zone", "Borough"]]
    by_zone = by_zone.reindex(names.index, fill_value=0).astype("int64").sort_values(ascending=False)
    print("\n-- top 10 pickup zones --")
    print(names.join(by_zone.rename("trips")).loc[by_zone.index[:10]].to_string())
    print("\n-- zones with fewest pickups --")
    print(names.join(by_zone.rename("trips")).loc[by_zone.index[-5:]].to_string())

    print("\n-- trips by hour of day --")
    print(by_hour.astype("int64").sort_index().to_string())

    print("\n-- dropoff borough --")
    print(dropoffs.astype("int64").sort_values(ascending=False).to_string())

    print("\n-- data quality counts (left for the data preparation step) --")
    quality = ["duplicate_rows", "dropoff_not_after_pickup", "longer_than_6h", "dropoff_zone_unknown"]
    print(summary[quality].sum().to_string())

    print("\n-- weather at pickup --")
    print(f"trips in an hour with rain:     {rain_trips:,}")
    print(f"trips in an hour with snowfall: {snow_trips:,}")

    print(f"\n== {config.WEATHER_FILE.name} ==")
    print(f"rows: {len(weather):,}  zones: {weather['LocationID'].nunique()}  "
          f"hours per zone: {len(weather) // weather['LocationID'].nunique()}")
    print(weather[config.WEATHER_VARIABLES].describe().round(2).to_string())
    print(f"zone-hours with rain > 0:     {(weather['rain'] > 0).mean():.1%}")
    print(f"zone-hours with snowfall > 0: {(weather['snowfall'] > 0).mean():.1%}")
    grid = weather.groupby("LocationID")[["grid_latitude", "grid_longitude"]].first()
    print(f"distinct Open-Meteo grid cells used: {len(grid.drop_duplicates())} for {len(zones)} zones")


if __name__ == "__main__":
    main()
