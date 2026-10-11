# NYC Taxi Demand Forecasting

Hourly taxi demand forecasting for 138 Manhattan and Queens pickup zones using
Yellow and Green Taxi data, calendar features, lagged demand, rolling demand,
and weather variables.

## Project scope

- **Geography:** Manhattan and Queens, 69 zones each
- **Taxi types:** Yellow and Green Taxi
- **Study period:** September 2025 to February 2026
- **Target:** hourly pickup count per zone (`trip_count`)
- **Modeling grain:** one row per pickup zone and hour
- **Evaluation:** chronological train/test split with MAE, RMSE, and R²

The raw trip data contains 23,318,979 trips and is approximately 3.2 GB. It is
not stored in GitHub. Teammates can obtain it from the private
[Kaggle dataset](https://www.kaggle.com/datasets/adithyaajay1210/nyc-taxi-demand-manhattan-queens),
or rebuild it with the data-collection notebook.

## Data sources

| Source | Used for |
|---|---|
| [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) | Trip pickup/dropoff times and taxi zones |
| [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) | Hourly apparent temperature, rain, snowfall, and precipitation probability |

See [data/DATA_GUIDE.md](data/DATA_GUIDE.md) for dataset access, file layouts,
field descriptions, memory considerations, and known data issues.

## Setup

Create or activate a Python environment, then install the base dependencies:

```bash
pip install -r requirements.txt
```

The modeling notebooks additionally require scikit-learn and joblib:

```bash
pip install scikit-learn joblib
```

Open notebooks in VS Code with the Jupyter extension and select the same Python
environment as the notebook kernel.

## Reproduction workflow

Run the notebooks in this order from the repository root.

### 1. Collect the data

Open [scripts/data_collection.ipynb](scripts/data_collection.ipynb) and run all
cells. This downloads the TLC source files, collects zone-level weather, joins
weather to trips, and writes files under `data/raw/`. The first run downloads
approximately 425 MB and requires network access.

The small zone, weather, and collection-summary files are already in the
repository. The large trip CSV is not.

### 2. Process and engineer features

Run [scripts/data_processing_engineering.ipynb](scripts/data_processing_engineering.ipynb).
It cleans the trip data, aggregates demand to zone-hour rows, fills missing
zone-hours, joins weather and calendar variables, and creates lag and rolling
demand features.

Main outputs:

- `data/processed/features.csv`
- `data/processed/features_manhattan.csv`
- `data/processed/features_queens.csv`
- `data/processed/cleaning_report.md`

### 3. Run exploratory data analysis

The main reproducible EDA implementation is:

```bash
python scripts/eda_arun.py
python scripts/validate_eda_arun.py
```

The analysis can also be run from [scripts/EDA_Arun.ipynb](scripts/EDA_Arun.ipynb).
Individual issue groups can be rerun, for example:

```bash
python scripts/eda_arun.py --issues 63
python scripts/eda_arun.py --issues 64
python scripts/eda_arun.py --issues 65
python scripts/eda_arun.py --issues 66
```

EDA outputs are saved under `EDA_doc/figures/` and `EDA_doc/tables/`. Findings
and interpretation are summarized in [EDA_doc/EDA_findings.md](EDA_doc/EDA_findings.md).
See [EDA_doc/README.md](EDA_doc/README.md) for issue coverage and reproducibility
details.

### 4. Prepare the modeling split and baseline

Run [models/modeling_preparation_baseline.ipynb](models/modeling_preparation_baseline.ipynb).
It creates an 80/20 chronological split using unique timestamps, so every zone
at the same hour is assigned to the same partition. It also evaluates the naive
168-hour historical baseline.

### 5. Train the models

Run these notebooks in order:

1. [models/model_1_linear_regression.ipynb](models/model_1_linear_regression.ipynb)
2. [models/model_2_random_forest.ipynb](models/model_2_random_forest.ipynb)
3. [models/model_3_hist_gradient_boosting.ipynb](models/model_3_hist_gradient_boosting.ipynb)

The models use the same train/test split and the same core feature groups:

- pickup location
- hour, day of week, and month
- holiday indicator
- apparent temperature, rain, snowfall, and precipitation probability
- 1-hour, 24-hour, and 168-hour demand lags
- 3-hour and 24-hour rolling demand

Model 3 uses Poisson loss and explicitly marks the ordinal-encoded categorical
features as categorical features.

### 6. Compare models

Run [models/model_comparison_error_analysis.ipynb](models/model_comparison_error_analysis.ipynb)
for the final comparison, train/test gaps, hourly errors, zone errors, residuals,
and largest individual errors.

### 7. Prepare the time-series dataset (Review 2)

Run [scripts/time_series_data_preparation.ipynb](scripts/time_series_data_preparation.ipynb).
It builds on `data/processed/features.csv`, recovers the dropped warm-up week
(1-7 Sep) exactly from its 168-hour lag column so the series cover the full
history, and writes analysis-ready series to `data/processed/time_series/`:

- hourly and daily series for all zones, each borough and each service area
- the zone-hour and zone-day panels
- a calendar and event table (holiday names, holiday periods, special days and
  nights, DST flags, heavy-snow days, daily and weekly Fourier terms)
- train/validation/test splits that reuse the ML test period, plus rolling-origin
  folds
- per-zone demand profiles and readiness diagnostics
- a feature catalogue giving every column's role (target, known-in-advance
  regressor, weather regressor, trend or descriptive), checked for leakage,
  extrapolation and collinearity

Every step, file and field is documented in
[data/dataset-documents/time_series_preparation.md](data/dataset-documents/time_series_preparation.md).
All inputs are in the repository, so this step does not need the Kaggle data.

### 8. Run time-series analysis and forecasting (Review 2)

Review 2 **Model 1** is grouped in `models/time_series/model_1/`.
The completed Review 2 workflow is separate from the Review 1 regression models.
Start with the [executed analysis notebook](models/time_series/model_1/time_series_analysis1.ipynb),
[results and reproduction guide](models/time_series/model_1/README.md).

```bash
pip install -r requirements.txt -r requirements-time-series.txt
python models/time_series/model_1/test_time_series.py
python models/time_series/model_1/run_time_series.py
python models/time_series/model_1/validate_time_series.py
```

This contribution uses adaptive seasonal profiles, TSB intermittent-demand forecasting,
and coherent bottom-up aggregation. It includes training-only median-profile decomposition,
stationarity and dependence analysis, 24-hour and 168-hour forecasts, interval calibration,
event/error analysis, and an unscored historical next-week forecast.

The teammate's Dynamic Harmonic Regression (ARIMA + Fourier) and MSTL + ETS models
are excluded from this branch's current implementation. Standalone ETS and ARIMA
comparisons are also removed.

The zone approach reduces day-ahead MAE from **9.3074 to 7.8200** (16.0%).
Its summed forecast reduces combined-hourly MAE from **777.71 to 649.37** (16.5%).
Daily adaptive forecasting reduces combined-daily MAE by **10.5%**.
Four pre-test folds select models; two later weeks calibrate intervals.
This ownership-driven revision reuses an already examined historical holdout;
a fresh evaluation period is needed for a new blind confirmation.

Review 1 uses observed recent-demand features; these Review 2 forecasts hide
every outcome inside the issued day/week. The scores answer different
forecasting questions and are not an equal-information model ranking.

## Review 1 modeling results
## Association-rule data preparation

The Review 2 transaction preparation is available separately from the modelling
workflow. It uses the same chronological split and fits demand/temperature bins
and zone clusters on training data only.

```bash
python scripts/association_rule_data_preparation.py
python scripts/association_rule_data_preparation.py --validate-only
python -m unittest discover -s tests -v
```

See [ARM_doc/README.md](ARM_doc/README.md) and
[data/dataset-documents/association_rule_preparation.md](data/dataset-documents/association_rule_preparation.md)
for category definitions, audit/exclusion details, sparse Boolean outputs and the
mining handoff. The executed
[scripts/association_rule_data_preparation.ipynb](scripts/association_rule_data_preparation.ipynb)
shows the preparation and readiness charts. Outputs go to
`data/processed/association_rules/`. Frequent-itemset mining and rule evaluation
remain the next stages.

## Current modeling results

The official test period is chronological:

- **Training:** `2025-09-08 00:00` to `2026-01-25 03:00`
- **Testing:** `2026-01-25 04:00` to `2026-02-28 23:00`
- **Training rows:** 460,920
- **Test rows:** 115,368

| Model | Test MAE | Test RMSE | Test R² |
|---|---:|---:|---:|
| Naive 168-hour baseline | 9.3074 | 24.0566 | 0.8776 |
| Linear Regression | 7.4861 | 15.7036 | 0.9478 |
| Random Forest Regressor | 6.7993 | 15.2593 | 0.9507 |
| HistGradientBoosting Regressor | 5.7841 | 13.1632 | 0.9633 |

## Feature importance

Model 2 saves Random Forest impurity importance to
`models/modeling/model_2_feature_importance.csv`.

Model 3 saves permutation importance to
`models/modeling/model_3_permutation_importance.csv`. It shuffles a feature on
a sample of up to 20,000 test rows and measures the change in negative MAE.
The strongest Model 3 predictors were the 1-hour lag, 24-hour lag, 24-hour
rolling demand, 168-hour lag, pickup location, and hour of day.

These rankings describe predictive usefulness for the fitted model. They are
not causal effects.

## Output layout

Modeling outputs are written to `models/modeling/`:

```text
train.csv
test.csv
split_summary.csv
baseline_168h_predictions.csv
baseline_metrics.csv
model_1_predictions.csv
model_1_metrics.csv
model_1_coefficients.csv
model_2_predictions.csv
model_2_metrics.csv
model_2_feature_importance.csv
model_3_predictions.csv
model_3_metrics.csv
model_3_permutation_importance.csv
model_comparison_final.csv
model_improvement_vs_baseline.csv
model_train_test_comparison.csv
model_error_by_hour.csv
model_3_error_by_zone.csv
model_3_largest_errors.csv
```

Serialized model files are local artifacts. The large Random Forest `.joblib`
file is excluded from GitHub because it exceeds GitHub's 100 MB file limit.

## Repository structure

```text
data/
  DATA_GUIDE.md
  dataset-documents/       collection, processing and time-series preparation docs
  raw/                     zones, weather, collection summary, large local data
  processed/               cleaned and feature-engineered datasets
    time_series/           analysis-ready series for the time-series stage
EDA_doc/
  EDA_findings.md
  README.md
  figures/
  tables/
models/
  modeling_preparation_baseline.ipynb
  model_1_linear_regression.ipynb
  model_2_random_forest.ipynb
  model_3_hist_gradient_boosting.ipynb
  model_comparison_error_analysis.ipynb
scripts/
  data_collection.ipynb
  data_processing_engineering.ipynb
  time_series_data_preparation.ipynb
  EDA_Arun.ipynb
  eda_arun.py
  validate_eda_arun.py
requirements.txt
```

## Limitations and project status

- Review 1 models are first-pass baselines. Review 2 compares fixed statistical
  candidates through rolling-origin validation; it does not claim exhaustive
  hyperparameter search or universal superiority over seasonal naive forecasts.
- The large raw trip CSV is external to GitHub.
- Association-rule mining and an interactive dashboard are not implemented in
  the current repository. Association-rule data preparation is ready for the
  mining stage.
- [scripts/EDA_visuallization.ipynb](scripts/EDA_visuallization.ipynb) is a legacy
  visualization notebook and may contain stale dataset paths; use the Arun EDA
  implementation for the reproducible current analysis.
