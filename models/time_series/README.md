# Review 2 time-series analysis

This stage reads the prepared CSV files without modifying them.
The target is DST-adjusted hourly pickups in Manhattan and Queens, not all NYC.

## Evaluation protocol

- The first four supplied weekly folds select each aggregate series' model by MAE.
- Folds five and six are reserved for interval calibration and independent validation.
- The official hourly holdout is 25 January 2026 04:00 through 28 February 2026 23:00.
- Forecasts are issued every 24 hours and every 168 hours. All demand inside a forecast
  block is hidden until the next origin. The last block is shorter.
- Both operational schedules use the model selected for the weekly task. Day-ahead
  results therefore measure this fixed model at a shorter horizon, not a separately
  optimized model.
- Daily models use complete calendar days, so their test starts at midnight on
  25 January. Daily scores cannot be compared directly with the hourly window.
- Only calendar regressors known in advance enter models. Archived weather and
  retrospective snow flags are used for error analysis, never as future inputs.
- Hyperparameters are fixed; the limited model search is the candidate list in
  scripts/tsa/config.py. No test-driven tuning or best-test-model selection.
- Rolling refits may use earlier observed test blocks, never the current block.
- Point forecasts are nonnegative. Log-model forecasts are back-transformed without
  mean-bias correction, appropriate to MAE-oriented median point prediction.
- Confidence claims must account for autocorrelation, only four selection weeks,
  two calibration weeks, five test weeks, and a winter storm distribution shift.
- Zone totals are coherent by bottom-up aggregation; independently fitted aggregate
  forecasts are a separate experiment and need not agree with zone forecasts.
- Review 1 scores use observed short lags and archived weather; they are context,
  not an equal-information day-ahead/week-ahead contest.

Code, figures, metrics, and the presentation notebook belong in the repository.
The owner's extended explanation and viva reference are kept outside this repo.

