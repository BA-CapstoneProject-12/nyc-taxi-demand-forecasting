"""Fixed protocol. These choices are made before evaluating test outcomes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/processed/time_series"
OUT = ROOT / "models/time_series"
TABLES = OUT / "tables"
FIGURES = OUT / "figures"
SEED = 42
TARGET = "trip_count_adj"
SERIES = ["All zones", "Manhattan", "Queens", "Yellow Zone", "Boro Zone", "Airports"]
# Existing folds 1-4 select models; folds 5-6 calibrate intervals independently.
SELECTION_FOLDS = (1, 2, 3, 4)
CALIBRATION_FOLDS = (5, 6)
HOURLY_MODELS = (
    "naive_24", "naive_168", "mean_4weeks", "adaptive_week",
    "harmonic_ar", "harmonic_ar_calendar", "mstl_ets",
)
DAILY_MODELS = ("naive_7", "ets_weekly", "sarima_weekly")
ZONE_MODELS = ("naive_168", "mean_4weeks", "adaptive_week", "tsb")
EVENT_FEATURES = (
    "is_holiday", "is_day_before_holiday", "is_day_after_holiday",
    "is_holiday_period", "is_special_day", "is_night_event",
)

def ensure_output():
    for path in (OUT, TABLES, FIGURES):
        path.mkdir(parents=True, exist_ok=True)

