"""Create chronological train, validation, and test datasets from features.csv."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "processed" / "features.csv"
OUTPUT_DIR = ROOT / "timeSeries" / "dataset"


def print_split_summary(name: str, split: pd.DataFrame) -> None:
    """Print the date range and size of a dataset split."""
    timestamps = split["pickup_hour"]
    print(
        f"{name}: "
        f"date range={timestamps.min()} to {timestamps.max()}, "
        f"rows={len(split)}, "
        f"unique timestamps={timestamps.nunique()}"
    )


def main() -> None:
    """Read features.csv, create chronological splits, and save them."""
    if not SOURCE_PATH.is_file():
        raise FileNotFoundError(f"Source dataset not found: {SOURCE_PATH}")

    features = pd.read_csv(SOURCE_PATH, parse_dates=["pickup_hour"])
    if features["pickup_hour"].isna().any():
        raise ValueError("pickup_hour contains missing or invalid timestamps.")

    features = features.sort_values("pickup_hour", kind="mergesort").reset_index(drop=True)
    timestamps = features["pickup_hour"].drop_duplicates().sort_values().reset_index(drop=True)
    timestamp_count = len(timestamps)

    train_timestamp_count = int(timestamp_count * 0.70)
    validation_timestamp_count = int(timestamp_count * 0.15)
    train_end = train_timestamp_count
    validation_end = train_end + validation_timestamp_count

    train_timestamps = set(timestamps.iloc[:train_end])
    validation_timestamps = set(timestamps.iloc[train_end:validation_end])

    train = features[features["pickup_hour"].isin(train_timestamps)]
    validation = features[features["pickup_hour"].isin(validation_timestamps)]
    test = features[~features["pickup_hour"].isin(train_timestamps | validation_timestamps)]

    if train.empty or validation.empty or test.empty:
        raise ValueError("The dataset is too small to create three non-empty splits.")

    if train["pickup_hour"].max() >= validation["pickup_hour"].min():
        raise AssertionError("Train and validation timestamps overlap or are out of order.")
    if validation["pickup_hour"].max() >= test["pickup_hour"].min():
        raise AssertionError("Validation and test timestamps overlap or are out of order.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    train.to_csv(OUTPUT_DIR / "train.csv", index=False)
    validation.to_csv(OUTPUT_DIR / "val.csv", index=False)
    test.to_csv(OUTPUT_DIR / "test.csv", index=False)

    print(f"Source: {SOURCE_PATH}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Total unique timestamps: {timestamp_count}")
    print_split_summary("Train", train)
    print_split_summary("Validation", validation)
    print_split_summary("Test", test)


if __name__ == "__main__":
    main()
