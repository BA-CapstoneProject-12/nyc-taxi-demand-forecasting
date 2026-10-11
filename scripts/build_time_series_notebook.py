"""Build and execute the review notebook using the already evaluated artifacts."""
from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]
nb=nbf.v4.new_notebook()
nb.metadata.kernelspec={"display_name":"Python 3","language":"python","name":"python3"}
cells=[]
def md(text):cells.append(nbf.v4.new_markdown_cell(text))
def code(text):cells.append(nbf.v4.new_code_cell(text))
md("""# Review 2: taxi demand through time
**Manhattan + Queens | 138 zones | September 2025-February 2026**

This executed notebook presents a reproducible forecasting study, from input reconciliation
and temporal diagnostics to untouched-test evaluation and historical next-week forecasts.
Run `python scripts/run_time_series.py` to refit and regenerate the evidence.
This notebook reads those outputs so a reviewer can explore results without retraining.""")
code("""from pathlib import Path
import json
import pandas as pd
from IPython.display import display, Image, HTML
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'data/processed/time_series').exists())
TABLES = ROOT / 'models/time_series/tables'
FIGURES = ROOT / 'models/time_series/figures'
def table(name): return pd.read_csv(TABLES / name)
def figure(name): display(Image(filename=str(FIGURES / name)))
pd.set_option('display.max_columns', 15)
pd.set_option('display.float_format', lambda x: f'{x:,.3f}')
""")
md("""## 1. Data integrity and forecasting question
We forecast **completed pickups**, not latent rider demand or vehicle requirements.
All 11 prepared CSV files are inventoried and hashed. Zone counts reconcile with each
aggregation and with 22,579,793 cleaned trips. Hourly test targets match Review 1 exactly.
The merged DST hour is adjusted to an average hourly rate; the original two timestamps
cannot be reconstructed. The daily adjusted total is therefore not the observed trip total
on the DST date.""")
code("""display(table('input_checks.csv'))\ndisplay(table('input_manifest.csv')[['path','rows','columns']])""")
md("""## 2. Honest chronological evaluation
- Supplied folds 1-4 (14 December-10 January): choose the smallest pooled MAE per series.
- Folds 5-6 (11-24 January): independent calibration; never used to select models.
- Hourly test: 25 January 04:00-28 February 23:00, 836 hours.
- Issue a fresh forecast every 24 or 168 hours, observing only previous blocks.
- Use the weekly-selected model at both horizons; day-ahead scores are not separately tuned.
- Daily series use full calendar days and start their test four hours earlier.
- Archived weather and retrospective heavy-snow flags are excluded from predictors.

The first four folds overlap the prepared training label: each fit still cuts its own
history at its forecast origin. This is expanding-window cross-validation, not random CV.
Only six months are observed, so annual seasonality is not identifiable.""")
code("""figure('01_series_overview.png')""")
md("""## 3. Trend, daily cycles, and weekly cycles
MSTL separates `log(1 + pickups)` into trend, a 24-hour component, a 168-hour component,
and a residual. Decomposition is fitted on training data only. Seasonal strength is
`max(0, 1 - Var(residual) / Var(residual + component))`; it is descriptive, not forecast accuracy.""")
code("""figure('02_mstl_decomposition.png')\ndisplay(table('seasonal_strength.csv').pivot(index='series_id',columns='component',values='strength'))\nfigure('04_weekly_heatmaps.png')""")
md("""## 4. Dependence and stationarity
ADF tests a unit-root null; KPSS tests a level-stationary null. Their disagreement is useful
evidence, not permission to keep differencing until every p-value is small. Tests use the
training window, a constant term, ADF AIC lag selection up to 24, and automatic KPSS lags.
KPSS p-values can be bounded by its lookup table; warnings are saved.
Daily/weekly spectral peaks motivate multiple seasonal components.""")
code("""figure('03_dependence_spectrum.png')\ndisplay(table('stationarity.csv').query("series_id == 'All zones'").drop(columns='warnings'))""")
md("""## 5. Candidate models
| Model | Mechanism |
|---|---|
| Daily/weekly naive | Repeat the final observed 24/168-hour cycle |
| Four-week mean | Average four matching past weekly cycles |
| Adaptive week | Four-week profile, recent 24-hour level ratio, 48-hour exponential damping |
| Harmonic AR | Daily Fourier K=6 + weekly K=16 (skip duplicate daily frequencies), ridge alpha=3, then AR(2) errors |
| Harmonic AR + calendar | Same model plus six holiday/event indicators known in advance |
| MSTL-ETS | Robust log MSTL (24,168), damped Holt on seasonally adjusted series, repeat final seasonal components |
| Daily SARIMA | Log SARIMA (1,0,1)(1,1,0)[7] |
| Daily ETS | Log damped additive trend + additive weekly seasonality |
| Zone TSB | Exponentially smooth occurrence probability and positive demand size |

Harmonic fits use the last 12 weeks with a six-week weight half-life. MSTL forecasts also
use the last 12 weeks. Harmonic regression is a two-stage approximation, **not jointly fitted
SARIMAX**. Log forecasts use expm1 without a mean correction: point predictions are
median-oriented, matching MAE selection. No test-dependent parameter search is performed.""")
code("""display(table('hourly_selection.csv').sort_values(['series_id','selection_MAE']))\nfigure('05_rolling_validation.png')""")
md("""## 6. Measured holdout performance
MAE/RMSE are pickups per hour at the specified series aggregation. WAPE is aggregate
absolute error divided by total observed pickups; it remains undefined for zero total.
MASE scales MAE by pre-test weekly-naive differences. Positive bias means overforecasting.
The weekly baseline obeys the same origin and horizon as each evaluated model.""")
code("""display(table('hourly_test_metrics.csv'))\nfigure('06_holdout_improvement.png')\ndisplay(table('paired_block_bootstrap.csv'))""")
md("""The paired bootstrap resamples whole forecast-origin blocks (2,000 draws, fixed seed).
There are only five weekly test blocks, and neighboring blocks may remain dependent.
Treat intervals for MAE improvement as exploratory, not definitive significance tests.""")
md("""## 7. Forecast intervals and calibration
Absolute calibration errors give empirical 80% and 95% radii, separately by series and
issuance schedule. Lead bins: 1-6/7-12/13-24 for day-ahead; 1-24/25-72/73-168 for week-ahead.
The finite-sample rank is ceil((n+1) x coverage), capped at n. Lower bounds are clipped at zero.
Calibration has only two weeks and cannot guarantee coverage after a demand shift.
These are marginal hourly bands; adding endpoints does not produce a calibrated weekly-total band.""")
code("""figure('07_forecast_intervals.png')\ndisplay(table('interval_metrics.csv'))\nfigure('09_interval_coverage.png')""")
md("""## 8. Residuals and demand shocks
Inspect bias, tails, serial dependence, and storm/holiday subsets. Heavy-snow indicators
are retrospective descriptive labels. They do not establish a causal storm effect.
Ljung-Box is applied to **multi-step forecast errors**, whose dependence is expected;
these are not independent one-step model innovations.""")
code("""figure('08_residual_diagnostics.png')\nfigure('11_event_stress_test.png')\ndisplay(table('event_hour_errors.csv').query("series_id == 'All zones' and dimension == 'is_heavy_snow_day'"))\ndisplay(table('daily_error_totals.csv').query("series_id == 'All zones' and schedule == 24").head(10))\ndisplay(table('peak_hour_recall.csv').groupby(['series_id','schedule']).top_decile_recall.mean().unstack())""")
md("""## 9. All 138 zones and coherent totals
Each zone chooses among four candidates using folds 1-4. TSB handles sparse demand;
zero-demand zones stay in evaluation. Four folds provide limited protection from per-zone
selection noise. Zone forecasts sum exactly to borough/service-area totals and the combined
total. Independently modeled aggregate forecasts are separate and are not forced to match.""")
code("""display(table('zone_selection.csv').groupby(['demand_pattern','model']).size().unstack(fill_value=0))\ndisplay(table('zone_test_metrics.csv'))\ndisplay(table('zone_group_metrics.csv'))\nfigure('10_zone_errors.png')\ndisplay(table('bottom_up_metrics.csv'))""")
md("""### Measured gains and uncertainty for coherent totals
Day-ahead zone MAE falls from **9.3074 to 7.8200** (16.0%). Summing those forecasts gives
combined-demand MAE **649.37**, versus **777.71** for weekly naive (16.5%).
The zone approach was specified before test evaluation. These gains do not erase the
independent aggregate model failures shown earlier.
Aggregate bands below are calibrated on summed zone forecast errors before test; they are
not obtained by adding zone interval endpoints. Marginal interval bounds need not reconcile.""")
code("""figure('13_bottom_up_improvement.png')
display(table('bottom_up_interval_metrics.csv'))""")
md("""## 10. Daily forecasting and the Review 1 context
Daily models answer a seven-calendar-day planning question; their test includes the first
four hours of 25 January excluded from the hourly test. Review 1 used observed short lags
and archived weather. Its scores answer a different information-availability question and
must not be advertised as directly beaten by a longer-horizon model.""")
code("""display(table('daily_test_metrics.csv'))\ndisplay(pd.read_csv(ROOT / 'models/modeling/model_comparison_final.csv'))""")
md("""## 11. Historical next-week forecast
The example below is issued at **1 March 2026 00:00**, after the last available observation,
and covers 1-7 March. It is an unscored historical extrapolation, not a current live forecast.
Its event calendar is checked for that exact week. No observed weather is supplied.
Historical calibration bands may fail to transfer to the new regime.""")
code("""figure('12_next_week_forecast.png')\ndisplay(table('aggregate_forecast_next_week.csv').query("series_id == 'All zones'").head(24))""")
md("""## 12. What to defend in the review
1. Multiple seasonality is supported by independent decomposition, ACF, and spectral evidence.
2. Strong seasonal baselines are essential; complexity is accepted only by pre-test validation.
3. Forecast horizon and information available at issue time define the prediction problem.
4. Uncertainty quality is measured through coverage, width, and interval scores.
5. Demand shocks expose limits of calendar-only forecasts.
6. Sparse zones need different treatment from busy zones; aggregate consistency is checked.
7. Six months, few holidays, five weekly test blocks, and winter-specific holdout limit generalization.
8. To improve operational deployment, obtain vintage weather forecasts, extend to multiple years,
   calibrate on more forecast origins, and validate on a new untouched period.

Sources: [MSTL](https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.MSTL.html),
[dynamic harmonic regression](https://otexts.com/fpp3/dhr.html),
[time-series cross-validation](https://otexts.com/fpp3/tscv.html).

All assertions and exported metric checks are reproducible with
`python scripts/test_time_series.py` and `python scripts/validate_time_series.py`.
The extended personal reference document is intentionally outside the repository.""")
code("""display(table('output_checks.csv').groupby('passed').size().rename('checks'))""")
nb.cells=cells
path=ROOT/"models/time_series_analysis.ipynb"
NotebookClient(nb,timeout=180,kernel_name="python3",resources={"metadata":{"path":str(ROOT)}}).execute()
nbf.write(nb,path)
print(f"Saved executed notebook: {path} ({len(cells)} cells)")
