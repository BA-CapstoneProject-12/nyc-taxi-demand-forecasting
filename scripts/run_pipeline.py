"""Run the full data collection, start to finish.

    python scripts/run_pipeline.py

Steps:
  1. collect_zones   - Manhattan and Queens zones with centroid lat/lon
  2. collect_weather - hourly weather for each zone centroid
  3. collect_taxi    - yellow + green trips picked up in those zones
  4. build_dataset   - every trip with the weather at its pickup zone and hour
"""
import build_dataset
import collect_taxi
import collect_weather
import collect_zones

STEPS = [collect_zones, collect_weather, collect_taxi, build_dataset]


def main():
    for step in STEPS:
        print(f"\n=== {step.__name__} ===")
        step.main()


if __name__ == "__main__":
    main()
