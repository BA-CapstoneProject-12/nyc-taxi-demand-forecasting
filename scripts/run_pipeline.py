"""Run the full data collection, start to finish.

    python scripts/run_pipeline.py

Steps:
  1. collect_zones   - Staten Island zones and their centroid lat/lon
  2. collect_taxi    - yellow + green trips picked up in Staten Island
  3. collect_weather - hourly weather for each zone centroid
  4. build_dataset   - one row per trip with the weather at pickup
"""
import build_dataset
import collect_taxi
import collect_weather
import collect_zones

STEPS = [collect_zones, collect_taxi, collect_weather, build_dataset]


def main():
    for step in STEPS:
        print(f"\n=== {step.__name__} ===")
        step.main()


if __name__ == "__main__":
    main()
