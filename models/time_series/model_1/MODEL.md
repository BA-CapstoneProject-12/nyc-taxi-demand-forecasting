# Model 1: adaptive seasonal and intermittent-demand forecasting

Yes, this is a statistical time-series forecasting model system. It estimates seasonal
demand and recent changes using past observations, then predicts unseen future hours.
The analysis and plots support evaluation; they are separate from the forecast equations.

## Where the model is

- [tsa/baselines.py](tsa/baselines.py): adaptive hourly/daily equations, seasonal mean,
  seasonal naive, and TSB occurrence/size updates.
- [tsa/models.py](tsa/models.py): hourly and daily forecast dispatch.
- [tsa/backtest.py](tsa/backtest.py): rolling-origin validation, selection, and aggregate evaluation.
- [tsa/zones.py](tsa/zones.py): selection for each zone and bottom-up aggregation.
- [tsa/future.py](tsa/future.py): aggregate next-week forecasting.
- [tables/hourly_selected.json](tables/hourly_selected.json): selected aggregate methods.
- [tables/zone_selection.csv](tables/zone_selection.csv): the selected method for each zone.
- [time_series_analysis1.ipynb](time_series_analysis1.ipynb): executed analysis and results.

## Main model equations

For lead h, the hourly seasonal profile B(h) averages the corresponding slots from
the latest four complete 168-hour cycles. The recent-level ratio is

r = clip((mean of last 24 observed hours + 1) /
         (mean of matching 24-hour windows at lags 168, 336, 504, 672 + 1), 0.5, 1.5).

The prediction is B(h) * [1 + (r - 1) * exp(-h / 48)], with h starting at 1.
The correction therefore fades over the forecast horizon. Daily adaptation uses four
7-day cycles, the latest observed day, and a two-day decay instead.

For sparse zones, TSB updates demand-occurrence probability p with beta=0.05
at each hour and positive-demand size z with alpha=0.10 only when demand is positive.
Its prediction is p*z. This is an intermittent-demand method. It does not fit
ARIMA/Fourier regression or an MSTL + ETS pipeline.

Four pre-test folds select a candidate for each series/zone by MAE. Seasonal naive
and four-week means are candidate benchmarks and may remain the selected forecast
where they validate better. Bottom-up totals sum the selected zone forecasts.

## What is fitted and saved

This implementation has no serialized .pkl/.joblib estimator or neural-network weights.
The fitted state is the seasonal profile and recent-level correction, or TSB's
occurrence probability and positive size. The functions reconstruct this state from
history at each forecast origin. Selection decisions, forecast values, evaluation
metrics, and interval calibration are saved in the tables folder. Saved selection
JSON/CSV files alone are not trained estimator objects.

All six direct aggregate series selected adaptive seasonal forecasts. Among 138 zones,
88 selected adaptive profiles, 25 four-week means, 17 TSB, and eight weekly naive.
The day-ahead zone MAE is 7.8200 versus 9.3074 for weekly naive (16.0% reduction).
Summed city-hour MAE is 649.37 versus 777.71 (16.5% reduction). These are historical
results for this study, not guarantees for unseen periods. The holdout was previously
examined during the scope revision; a fresh holdout is needed for blind confirmation.

## Verify and run

From the repository root:

```bash
python models/time_series/model_1/test_time_series.py
python models/time_series/model_1/run_time_series.py --stage hourly
python models/time_series/model_1/validate_time_series.py
```

The report stage writes error analysis, figures, and a historical next-week forecast.
