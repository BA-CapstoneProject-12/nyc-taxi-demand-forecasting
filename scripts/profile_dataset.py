"""Print a profile of the collected dataset (numbers quoted in docs/).

    python scripts/profile_dataset.py
"""
import pandas as pd

import config


def main():
    path = config.PROCESSED_DIR / f"{config.DATASET_NAME}.parquet"
    data = pd.read_parquet(path)
    weather = pd.read_csv(config.WEATHER_FILE)

    print(f"== {path.name} ==")
    print(f"rows: {len(data):,}   columns: {data.shape[1]}")
    print(f"pickup range: {data['pickup_datetime'].min()} .. {data['pickup_datetime'].max()}")

    print("\n-- trips by taxi type and month --")
    month = data["pickup_datetime"].dt.strftime("%Y-%m")
    print(pd.crosstab(month, data["taxi_type"], margins=True).to_string())

    print("\n-- pickups by zone --")
    by_zone = data.groupby(["PULocationID", "pickup_zone"]).size().sort_values(ascending=False)
    print(by_zone.to_string())
    zones = pd.read_csv(config.ZONES_FILE)
    no_pickups = zones.loc[~zones["LocationID"].isin(data["PULocationID"]), "Zone"]
    print(f"zones with no pickups: {', '.join(no_pickups) or 'none'}")

    print("\n-- missing values per column --")
    print(data.isna().sum().to_string())

    print("\n-- data quality notes (left for the data preparation step) --")
    duration = data["dropoff_datetime"] - data["pickup_datetime"]
    subset = ["taxi_type", "pickup_datetime", "dropoff_datetime", "PULocationID", "DOLocationID"]
    print(f"exact duplicate trips:          {data.duplicated(subset=subset).sum()}")
    print(f"dropoff at or before pickup:    {(duration <= pd.Timedelta(0)).sum()}")
    print(f"trips longer than 6 hours:      {(duration > pd.Timedelta(hours=6)).sum()}")
    print(f"dropoff zone unknown (264/265): {data['DOLocationID'].isin([264, 265]).sum()}")
    print(f"dropoff also in {config.BOROUGH}:  {data['DOLocationID'].isin(zones['LocationID']).sum()}")
    print(f"median trip duration:           {duration.median()}")

    print("\n-- weather at pickup --")
    print(data[config.WEATHER_VARIABLES].describe().round(2).to_string())
    print(f"trips with rain > 0:          {(data['rain'] > 0).sum()}")
    print(f"trips with snowfall > 0:      {(data['snowfall'] > 0).sum()}")

    print("\n-- hourly weather table --")
    print(f"rows: {len(weather):,}  zones: {weather['LocationID'].nunique()}  "
          f"hours per zone: {len(weather) // weather['LocationID'].nunique()}")
    grid = weather.groupby("LocationID")[["grid_latitude", "grid_longitude"]].first()
    print(f"distinct Open-Meteo grid cells used: {len(grid.drop_duplicates())}")


if __name__ == "__main__":
    main()
