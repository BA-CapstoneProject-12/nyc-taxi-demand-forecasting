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

### 6. Compare models and test weather contribution

Run [models/model_comparison_error_analysis.ipynb](models/model_comparison_error_analysis.ipynb)
for the final comparison, train/test gaps, hourly errors, zone errors, residuals,
and largest individual errors.

Run [models/weather_ablation_histgradientboosting.ipynb](models/weather_ablation_histgradientboosting.ipynb)
to compare identical HistGradientBoosting models with and without weather
features. This measures predictive contribution, not causality.

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
weather_ablation_results.csv
weather_ablation_test_comparison.csv
weather_ablation_by_hour.csv
weather_ablation_by_zone.csv
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
  dataset-documents/       collection method and data dictionary
  raw/                     zones, weather, collection summary, large local data
  processed/               cleaned and feature-engineered datasets
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
  weather_ablation_histgradientboosting.ipynb
scripts/
  data_collection.ipynb
  data_processing_engineering.ipynb
  EDA_Arun.ipynb
  eda_arun.py
  validate_eda_arun.py
requirements.txt
```

## Limitations and project status

- The models are first-pass, untuned baselines; no hyperparameter search is
  included yet.
- The weather ablation is predictive, not causal.
- The large raw trip CSV is external to GitHub.
- Association-rule mining and an interactive dashboard are not implemented in
  the current repository.
- [scripts/EDA_visuallization.ipynb](scripts/EDA_visuallization.ipynb) is a legacy
  visualization notebook and may contain stale dataset paths; use the Arun EDA
  implementation for the reproducible current analysis.
