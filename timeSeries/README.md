# Time-Series Demand Forecasting

This folder contains the chronological time-series preparation, forecasting
models, evaluation notebooks, predictions, and diagnostic outputs for the NYC
taxi demand project.

## 1. What is being done

The goal is to forecast hourly taxi demand for each pickup zone
(`PULocationID`) using the cleaned processed dataset. The target variable is:

```text
trip_count
```

The workflow is:

1. Start from `data/processed/features.csv`.
2. Create chronological train, validation, and test partitions.
3. Keep all zones at the same timestamp in the same partition.
4. Fit each forecasting model separately for every pickup zone.
5. Select model configurations using validation error only.
6. Refit the selected configuration using training plus validation history.
7. Evaluate once on the untouched test period.
8. Save predictions, metrics, tuning results, and failure logs.

The data is not shuffled. Forecasts use only information available before the
forecast origin.

## 2. Dataset and splits

The source dataset is:

```text
data/processed/features.csv
```

The split-generation script is:

```text
timeSeries/create_time_series_split.py
```

The standard split is a chronological 70:15:15 split by unique
`pickup_hour`. All zones for one timestamp remain together:

```text
timeSeries/dataset/train.csv
timeSeries/dataset/val.csv
timeSeries/dataset/test.csv
```

Additional split variants are available for experiments:

```text
timeSeries/dataset/train80.csv
timeSeries/dataset/val10.csv
timeSeries/dataset/test10.csv

timeSeries/dataset/train60.csv
timeSeries/dataset/val20.csv
timeSeries/dataset/test20.csv
```

Each split preserves the original columns and zone-hour rows. The split files
are chronological and are not modified by the modeling notebooks.

## 3. Features

The processed feature table contains one row per pickup zone and hourly
timestamp. Its main columns are:

### Identifiers and target

| Column | Description |
|---|---|
| `PULocationID` | Pickup taxi zone identifier |
| `pickup_hour` | Hourly pickup timestamp |
| `trip_count` | Number of taxi trips starting in the zone and hour |

### Weather features

| Column | Description |
|---|---|
| `apparent_temperature` | Apparent temperature for the zone-hour |
| `rain` | Rain amount |
| `snowfall` | Snowfall amount |
| `precipitation_probability` | Precipitation probability |

### Calendar features

| Column | Description |
|---|---|
| `hour` | Hour of day |
| `day_of_week` | Day of week |
| `month` | Calendar month |
| `is_weekend` | Whether the timestamp falls on a weekend |
| `is_holiday` | Whether the date is a holiday |

### Historical target-derived features

| Column | Description |
|---|---|
| `trip_count_lag_1h` | Demand one hour earlier |
| `trip_count_lag_24h` | Demand one day earlier |
| `trip_count_lag_168h` | Demand one week earlier |
| `trip_count_roll_3h` | Three-hour rolling demand statistic |
| `trip_count_roll_24h` | Twenty-four-hour rolling demand statistic |

For forecasting, future target-derived values must not be read from the
evaluation files. The time-series models use historical target values through
the forecast origin and deterministic seasonal terms rather than future actual
demand.

## 4. Model 2: Dynamic Harmonic Regression

Notebook:

```text
timeSeries/model_2_dynamic_harmonic_regression.ipynb
```

The Model 2 copy notebook supports alternative split experiments:

```text
timeSeries/model_2_dynamic_harmonic_regression_copy.ipynb
```

The model is a dynamic harmonic regression model with ARIMA errors. Each
`PULocationID` is modeled independently as an hourly series.

### Fourier terms

Fourier sine and cosine terms represent:

- Daily seasonality: period of 24 hours.
- Weekly seasonality: period of 168 hours.

A small grid of daily harmonic counts, weekly harmonic counts, and ARIMA
orders is evaluated. The configuration with the lowest pooled validation MAE
is selected.

### ARIMA errors

The Fourier regressors explain deterministic seasonal structure. SARIMAX is
then used to model the remaining autocorrelated errors. The tested ARIMA
orders are intentionally small to keep per-zone fitting practical.

### Baseline

Model 2 is compared with a seasonal-naive baseline:

```text
forecast at time t = observed demand at time t - 168 hours
```

### Model 2 outputs

Depending on the experiment, outputs are written under:

```text
timeSeries/results/model_2/
timeSeries/results/model_2/Split801010/
timeSeries/results/model_2/Split602020/
timeSeries/results/model_2/Split751515/
```

Typical files include:

```text
metrics.csv
predictions.csv
fit_failures.csv
validation_candidate_summary.csv
validation_all_candidate_predictions.csv
zone_tuning_results.csv
```

## 5. Rolling-origin evaluation for Model 2

Notebook:

```text
timeSeries/rolling_func_model2.ipynb
```

This evaluation forecasts the test period in one-week horizons. The rolling
folds use 168-hour forecast windows. Fold numbering starts at 1.

After each forecast window is completed, its actual observations are appended
to the available history for the next fold. Actual values from a future fold
are not used while forecasting an earlier fold.

Outputs:

```text
timeSeries/results/model_2_rolling/rolling_origin_predictions.csv
timeSeries/results/model_2_rolling/rolling_origin_metrics.csv
timeSeries/results/model_2_rolling/rolling_origin_overall_metrics.csv
timeSeries/results/model_2_rolling/rolling_origin_failures.csv
```

## 6. Model 3: MSTL + ETS

Notebook:

```text
timeSeries/model_3_mstl_ets.ipynb
```

Model 3 also models each pickup zone separately. It combines:

- MSTL decomposition for multiple seasonal components.
- Daily and weekly seasonal structure.
- ETS/exponential smoothing for the deseasonalized trend and residual
  behavior.

Candidate trend and damping configurations are selected using validation MAE.
The selected configuration is refit on train plus validation data and then
evaluated on the test period.

Model 3 outputs are stored under:

```text
timeSeries/results/model_3/
```

Typical files include:

```text
metrics.csv
predictions.csv
fit_failures.csv
validation_candidate_summary.csv
validation_candidate_predictions.csv
zone_tuning_results.csv
```

## 7. Error analysis

Notebook:

```text
timeSeries/error_analysis_model2.ipynb
```

This notebook analyzes the rolling-origin Model 2 predictions, including:

- Fold-level error distributions.
- Daily MAE and RMSE.
- Zone-level errors.
- Hour-of-day errors.
- Largest absolute errors.
- Comparison of suspicious observations against
  `data/processed/features.csv`.

Its outputs are stored under:

```text
timeSeries/results/model_2_rolling/error_analysis/
```

## 8. Evaluation metrics

The notebooks report:

- **MAE**: mean absolute error.
- **RMSE**: root mean squared error.
- **R²**: coefficient of determination.
- **MAPE**: calculated only where actual demand is non-zero.

For MAPE, zero-actual rows are excluded rather than assigned an arbitrary
denominator. The number and percentage of excluded rows are reported.

Negative forecasts are clipped to zero where the model implementation
produces them, because taxi demand cannot be negative. Fit failures,
non-convergence, missing history, and insufficient history are recorded in
failure CSVs rather than silently treated as successful forecasts.

## 9. Leakage and data-integrity safeguards

The time-series workflow follows these rules:

- Splits are chronological.
- Timestamps are not shuffled.
- All zones at a timestamp remain in one partition.
- Validation configuration selection does not use test targets.
- Test forecasts use train plus validation history only.
- Rolling-origin forecasts use only history available before each origin.
- Future actual demand is not used as a predictor.
- Future target-derived lag and rolling values are not read from the
  evaluation partition.
- Prediction rows are aligned by `PULocationID` and `pickup_hour`.
- Source and prepared split files are treated as read-only model inputs.

