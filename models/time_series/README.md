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


## Run and review

```bash
pip install -r requirements.txt -r requirements-time-series.txt
python scripts/test_time_series.py
python scripts/run_time_series.py
python scripts/validate_time_series.py
python scripts/build_time_series_notebook.py
python scripts/catalog_time_series.py
python scripts/catalog_time_series.py --verify
```

The full fitting run takes several minutes on a typical laptop; MSTL refits are
the main cost. Individual stages: `--stage audit|diagnostics|hourly|daily|zones|report`.
After rerunning a stage, rerun output validation, the notebook builder, and the
catalog so the presentation and hashes match the latest artifacts.

Open [the executed notebook](../time_series_analysis.ipynb) or download and open
[the portable HTML report](review_2_results.html) in a browser. GitHub may display
HTML source instead of rendering the report. The HTML embeds all figures and works
offline. Full predictions are compressed CSV files that pandas reads directly.

## Measured results

| Approach | Task | Test MAE | Weekly-naive MAE | Reduction |
|---|---|---:|---:|---:|
| Per-zone selected models | 24-hour blocks, zone/hour | 7.8200 | 9.3074 | 16.0% |
| Per-zone selected models | 168-hour blocks, zone/hour | 8.0326 | 9.3074 | 13.7% |
| Sum of zone forecasts | 24-hour blocks, combined/hour | 649.37 | 777.71 | 16.5% |
| Sum of zone forecasts | 168-hour blocks, combined/hour | 675.57 | 777.71 | 13.1% |
| Daily ETS | 7-day blocks, combined/day | 12,288.08 | 14,270.20 | 13.9% |

The coherent zone approach was specified before holdout evaluation. Its 24-hour
combined forecast has R² 0.8616 and WAPE 13.97%. Its nominal 95% interval covers
94.38% of test hours. Intervals are calibrated on aggregate errors in the two
pre-test weeks; individual group bounds are marginal and do not themselves add up.

124 zones improve, eight tie, and six worsen against weekly naive at both
issuance schedules. Selected zone methods: adaptive seasonal 88, four-week mean
25, TSB 17, weekly naive 8.

Independent aggregate model selection chose harmonic regression with calendar
and AR(2) errors for combined demand, Manhattan, and Queens; MSTL-ETS for Yellow
Zone; and adaptive seasonal forecasts for Boro Zone and Airports. The selected
combined-demand and Manhattan models **underperform weekly naive on test**.
Their results are retained in `hourly_test_metrics.csv`, not replaced by the
coherent forecasts. Yellow Zone MSTL improves weekly forecasts but worsens
day-ahead forecasts. This supports separate horizon-specific validation in a
future study; the present study deliberately retains the fixed protocol.

Daily models selected ETS for five series and SARIMA (1,0,1)(1,1,0)[7] for Boro
Zone. All 252 hourly and 108 daily cross-validation candidate fits completed.
Check fit logs for warnings.

## Evidence map

- `tables/input_*.csv`: 43 input checks and checksums for all 11 source CSVs.
- `tables/stationarity.csv`, `acf_pacf.csv`, `periodogram.csv`,
  `seasonal_strength.csv`, `mstl_components.csv`: training-only diagnostics.
- `tables/*selection*`, `*selected.json`, `*cv*`, `*fit_log.csv`: candidate
  comparisons, selected models, fold evidence, and numerical fit status.
- `tables/hourly_test_metrics.csv`: independently fitted aggregate forecasts.
- `tables/zone_test_metrics.csv`, `zone_error_analysis.csv`,
  `bottom_up_metrics.csv`: per-zone and coherent aggregate results.
- `tables/*interval*`: calibration, interval coverage, width, and interval score.
- `tables/event_hour_errors.csv`, `daily_error_totals.csv`,
  `residual_ljung_box.csv`, `peak_hour_recall.csv`: where forecasts work/fail.
- `tables/*forecast_next_week.csv`: historical forecasts issued 1 March 2026
  for 1-7 March; unscored and not a live forecast.
- `tables/output_checks.csv`: 219 independent exported-result checks.
- `tables/environment.json`: versions and the Git commit when the initial run
  started. Source was being developed during that run; the final
  `source_manifest.csv` identifies the completed source files. This is not a
  claim that the initial commit alone contains the entire implementation.
- `tables/artifact_catalog.csv`: file catalog and checksums. Source/text hashes
  normalize line endings and a UTF-8 BOM; compressed/binary artifacts use raw bytes.

Eleven behavioral tests check forecasting information boundaries and zero-demand
edge cases. Thirteen figures and a 29-cell executed notebook provide the review
presentation. Original Review 1 notebooks and prepared input data remain unchanged.
