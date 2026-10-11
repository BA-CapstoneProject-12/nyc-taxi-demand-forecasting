# Model 1: seasonal and intermittent-demand forecasting

Model 1 forecasts completed taxi pickups for 138 zones in Manhattan and Queens. It uses the prepared hourly and daily time series in `data/processed/time_series/`. The target, `trip_count_adj`, adjusts the repeated daylight-saving hour.

## Forecasting flow

1. **Check the inputs.** Confirm that timestamps are complete, counts are valid, and zone totals agree with borough and combined totals.
2. **Describe the series.** Seasonal plots, decomposition, autocorrelation, and stationarity checks summarize patterns in the training data. These diagnostics do not feed future observations into the forecasts.
3. **Compare forecast methods.** Seasonal naive repeats a recent cycle; the four-week mean averages matching slots from prior weeks. The adaptive method starts with that four-week profile and applies a recent-level adjustment that fades over the forecast horizon. TSB separately updates the probability of a pickup and the size of positive demand, which is useful for intermittent zones.
4. **Select methods using past data.** Four weekly rolling-origin folds select a method by mean absolute error for each zone and each directly forecast aggregate series. At every forecast origin, the method uses only observations available before that origin.
5. **Forecast and aggregate.** Zone forecasts are issued in 24-hour and 168-hour blocks. Selected zone forecasts are summed to produce consistent borough, service-zone, and combined totals. Daily aggregate forecasts are evaluated separately.
6. **Measure uncertainty and error.** Two later pre-test folds calibrate 80% and 95% prediction intervals. The historical holdout is scored against seasonal naive using MAE, RMSE, WAPE, and other diagnostics.

The adaptive hourly forecast uses a four-week seasonal profile, compares the latest 24 hours with matching windows from earlier weeks, and gradually removes the resulting level adjustment. TSB forecasts are flat across each issued block; seasonal methods remain candidates for zones where weekly timing matters. See [MODEL.md](MODEL.md) for the equations and source locations.

## Files and results

- [time_series_analysis1.ipynb](time_series_analysis1.ipynb) contains the executed analysis.
- `tsa/` contains the forecasting, selection, diagnostics, interval, and reporting code.
- `figures/` contains the plots; `tables/` contains selections, predictions, metrics, checks, and manifests.
- `run_time_series.py` runs the analysis stages. `test_time_series.py` checks forecast behavior, and `validate_time_series.py` checks saved outputs.

From the repository root:

```bash
pip install -r requirements.txt -r requirements-time-series.txt
python models/time_series/model_1/test_time_series.py
python models/time_series/model_1/run_time_series.py
python models/time_series/model_1/validate_time_series.py
```

The runner also accepts `--stage audit|diagnostics|hourly|daily|zones|report`. The report stage writes error analysis, figures, and a historical next-week forecast.

The data cover September 2025 through February 2026, so they do not establish annual seasonality. The target measures observed completed pickups, not unmet demand. The historical holdout was examined during an earlier version of this work; a fresh period is needed for a blind evaluation.
