"""Error analysis, review figures, and a portable HTML results presentation."""
import base64
import html
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import acf
from .config import TABLES,FIGURES,OUT,TARGET,SERIES
from .diagnostics import savefig
from .future import next_week

def report(calendar,hourly,daily,profile):
    selected=json.loads((TABLES/"hourly_selected.json").read_text())
    p=pd.read_csv(TABLES/"hourly_intervals.csv.gz",parse_dates=["ds","origin"])
    p=p.merge(calendar[["is_heavy_snow_day","is_holiday","is_holiday_period"]],left_on="ds",right_index=True,validate="many_to_one")
    p["error"]=p.actual-p.prediction
    p["absolute_error"]=p.error.abs()
    p["hour"]=p.ds.dt.hour;p["date"]=p.ds.dt.normalize()
    from .metrics import scores
    groups=[]
    for (sid,schedule),g in p.groupby(["series_id","schedule"]):
        for dimension in ("is_heavy_snow_day","is_holiday","hour"):
            for value,block in g.groupby(dimension):
                groups.append(dict(series_id=sid,schedule=schedule,dimension=dimension,value=value,
                                   **scores(block.actual,block.prediction)))
    pd.DataFrame(groups).to_csv(TABLES/"event_hour_errors.csv",index=False)
    days=p.groupby(["series_id","schedule","date"]).agg(actual=("actual","sum"),prediction=("prediction","sum"),
                   hourly_MAE=("absolute_error","mean"),hours=("ds","size")).reset_index()
    days["total_error"]=days.prediction-days.actual
    days.sort_values("hourly_MAE",ascending=False).to_csv(TABLES/"daily_error_totals.csv",index=False)
    p.nlargest(100,"absolute_error").to_csv(TABLES/"largest_forecast_errors.csv",index=False)
    residuals=[]
    for (sid,schedule),g in p.groupby(["series_id","schedule"]):
        g=g.sort_values("ds")
        for lag,row in acorr_ljungbox(g.error,lags=[1,24,168],return_df=True).iterrows():
            residuals.append(dict(series_id=sid,schedule=schedule,lag=lag,statistic=row.lb_stat,p_value=row.lb_pvalue,
                                  note="Multi-step forecast errors; dependence is expected, not one-step innovations"))
    pd.DataFrame(residuals).to_csv(TABLES/"residual_ljung_box.csv",index=False)
    peak=[]
    for (sid,schedule,origin),g in p.groupby(["series_id","schedule","origin"]):
        if len(g)<24:continue
        n=max(1,int(np.ceil(.1*len(g))))
        true=set(g.nlargest(n,"actual").ds);forecast=set(g.nlargest(n,"prediction").ds)
        peak.append(dict(series_id=sid,schedule=schedule,origin=origin,
                         top_decile_recall=len(true&forecast)/n,peak_actual=g.actual.max(),
                         prediction_at_actual_peak=g.loc[g.actual.idxmax(),"prediction"]))
    pd.DataFrame(peak).to_csv(TABLES/"peak_hour_recall.csv",index=False)
    cv=pd.read_csv(TABLES/"hourly_fold_metrics.csv")
    fig,axes=plt.subplots(3,2,figsize=(14,12))
    for ax,sid in zip(axes.flat,SERIES):
        block=cv[cv.series_id.eq(sid)]
        for name,g in block.groupby("model"):
            ax.plot(g.fold,g.MAE,marker="o",lw=1,label=name)
        ax.axvspan(4.5,6.5,alpha=.12,color="#dd9a20")
        ax.set(title=sid,xlabel="Fold | shaded = calibration only",ylabel="MAE")
    axes[0,0].legend(fontsize=7,ncol=2)
    savefig("05_rolling_validation.png")
    metrics=pd.read_csv(TABLES/"hourly_test_metrics.csv")
    fig,axes=plt.subplots(1,2,figsize=(14,5))
    improvements=[]
    for ax,schedule in zip(axes,(24,168)):
        block=metrics[metrics.schedule.eq(schedule)]
        chosen=block[block.selected].set_index("series_id").reindex(SERIES)
        baseline=block[block.model.eq("naive_168")].set_index("series_id").reindex(SERIES)
        gain=100*(1-chosen.MAE/baseline.MAE)
        ax.barh(SERIES,gain,color=["#2e9479" if v>=0 else "#bc4749" for v in gain])
        ax.axvline(0,color="black",lw=.8);ax.set(title=f"{schedule}-hour forecast blocks",xlabel="MAE reduction vs weekly naive (%)")
        for sid,v in gain.items(): improvements.append(dict(series_id=sid,schedule=schedule,MAE_reduction_pct=v))
    pd.DataFrame(improvements).to_csv(TABLES/"improvement_vs_baseline.csv",index=False)
    savefig("06_holdout_improvement.png")
    city=p[p.series_id.eq("All zones")&p.schedule.eq(24)].sort_values("ds")
    fig,axes=plt.subplots(2,1,figsize=(15,9))
    for ax,mask,title in [(axes[0],city.ds.lt("2026-02-02"),"Opening test week: demand shock"),
                           (axes[1],city.ds.ge("2026-02-08")&city.ds.lt("2026-02-15"),"A later test week")]:
        g=city[mask]
        ax.fill_between(g.ds,g.lower_95,g.upper_95,color="#75bdd1",alpha=.25,label="95% empirical interval")
        ax.fill_between(g.ds,g.lower_80,g.upper_80,color="#75bdd1",alpha=.4,label="80% empirical interval")
        ax.plot(g.ds,g.actual,color="#263859",lw=1,label="Observed")
        ax.plot(g.ds,g.prediction,color="#dc7b2c",lw=1,label=selected["All zones"])
        ax.set(title=title,ylabel="Pickups/hour")
    axes[0].legend(ncol=2,fontsize=8)
    savefig("07_forecast_intervals.png")
    fig,axes=plt.subplots(2,2,figsize=(13,9))
    axes[0,0].plot(city.ds,city.error,lw=.7);axes[0,0].axhline(0,color="black",lw=.7);axes[0,0].set(title="Day-ahead forecast errors",ylabel="Actual - forecast")
    axes[0,1].hist(city.error,bins=45,color="#1f6e8c");axes[0,1].set_title("Error distribution")
    stats.probplot(city.error,dist="norm",plot=axes[1,0]);axes[1,0].set_title("Normal Q-Q: tail risk")
    axes[1,1].plot(np.arange(169),acf(city.error,nlags=168));axes[1,1].set(title="Error ACF (multi-step errors)",xlabel="Lag (hours)")
    savefig("08_residual_diagnostics.png")
    coverage=pd.read_csv(TABLES/"interval_metrics.csv")
    fig,axes=plt.subplots(1,2,figsize=(14,5))
    for ax,schedule in zip(axes,(24,168)):
        g=coverage[coverage.schedule.eq(schedule)]
        for target,offset,color in ((.8,-.18,"#1f6e8c"),(.95,.18,"#dd9a20")):
            vals=g[g.nominal_coverage.eq(target)].set_index("series_id").reindex(SERIES).coverage
            ax.bar(np.arange(6)+offset,vals,width=.34,color=color,label=f"{target:.0%} interval")
            ax.axhline(target,color=color,ls="--")
        ax.set(xticks=range(6),xticklabels=SERIES,ylim=(0,1.05),title=f"Measured coverage | {schedule} hours")
        ax.tick_params(axis="x",rotation=30);ax.legend()
    savefig("09_interval_coverage.png")
    z=pd.read_csv(TABLES/"zone_error_analysis.csv")
    g=z[z.schedule.eq(24)].nlargest(20,"MAE").sort_values("MAE")
    fig,ax=plt.subplots(figsize=(12,9))
    ax.barh(g.Zone,g.MAE,color="#1f6e8c",label="Selected model")
    ax.scatter(g.baseline_MAE,g.Zone,color="#dc7b2c",label="Weekly naive",zorder=3)
    ax.set(title="20 highest-error zones | 24-hour forecast blocks",xlabel="MAE (pickups/zone/hour)");ax.legend()
    savefig("10_zone_errors.png")
    fig,ax=plt.subplots(figsize=(14,5))
    g=days[days.series_id.eq("All zones")&days.schedule.eq(24)].sort_values("date")
    ax.plot(g.date,g.actual,marker="o",ms=3,label="Observed")
    ax.plot(g.date,g.prediction,marker="o",ms=3,label="Forecast")
    snow=calendar.groupby(calendar.index.normalize()).is_heavy_snow_day.max()
    for date in snow.index[snow]:
        if g.date.min()<=date<=g.date.max(): ax.axvspan(date,date+pd.Timedelta(days=1),color="#bc4749",alpha=.15)
    ax.set(title="Daily totals from day-ahead blocks | red = retrospective heavy-snow flags",
           ylabel="Pickups (first test date has 20 hours)")
    ax.legend();savefig("11_event_stress_test.png")
    next_week(calendar,hourly)
    f=pd.read_csv(TABLES/"aggregate_forecast_next_week.csv",parse_dates=["ds"])
    fig,ax=plt.subplots(figsize=(14,5))
    g=f[f.series_id.eq("All zones")]
    ax.fill_between(g.ds,g.lower_95,g.upper_95,color="#75bdd1",alpha=.3,label="95% historical calibration band")
    ax.plot(g.ds,g.prediction,color="#1f6e8c",label="Forecast")
    ax.set(title="Historical forecast issued 1 March 2026 | no observed outcomes available",ylabel="Pickups/hour")
    ax.legend();savefig("12_next_week_forecast.png")
    bottom=pd.read_csv(TABLES/"bottom_up_metrics.csv")
    base=metrics[metrics.model.eq("naive_168")][["series_id","schedule","MAE"]].rename(columns={"MAE":"baseline_MAE"})
    gains=bottom.merge(base,on=["series_id","schedule"],validate="one_to_one")
    gains["MAE_reduction_pct"]=100*(1-gains.MAE/gains.baseline_MAE)
    gains.to_csv(TABLES/"bottom_up_improvement.csv",index=False)
    fig,axes=plt.subplots(1,2,figsize=(14,5))
    for ax,schedule in zip(axes,(24,168)):
        g=gains[gains.schedule.eq(schedule)].set_index("series_id").reindex(SERIES)
        ax.barh(SERIES,g.MAE_reduction_pct,color="#2e9479")
        ax.set(title=f"Coherent zone totals | {schedule}-hour blocks",xlabel="MAE reduction vs weekly naive (%)")
        ax.axvline(0,color="black",lw=.7)
    savefig("13_bottom_up_improvement.png")
    write_html(metrics,coverage,selected)
    print("Error analysis, thirteen figures, and portable HTML report saved",flush=True)

def write_html(metrics,coverage,selected):
    def table(frame): return frame.to_html(index=False,float_format=lambda x:f"{x:,.3f}",border=0)
    sections=[
        "<h1>NYC taxi demand<br><span>Review 2 / Time-series analysis</span></h1>",
        "<p>138 Manhattan and Queens zones. 1 September 2025 to 28 February 2026. "
        "Forecasts use only observations available before their issue time.</p>",
        "<h2>What was tested</h2><p>Seven hourly candidates, three daily candidates, and four zone candidates. "
        "Four weekly origins select models; two later weeks calibrate uncertainty. The final 836 hours are the hourly test. "
        "Models are selected per series before test scoring. Daily and weekly issuance are evaluated separately.</p>",
        "<h2>Main outcomes: coherent forecasts from zones</h2>"+table(pd.read_csv(TABLES/"bottom_up_metrics.csv")),
        "<p>Zone forecasts reduce day-ahead zone MAE by 16.0% and their combined total reduces MAE by 16.5% "
        "versus weekly naive. These were evaluated as a predefined separate approach. No winner was substituted "
        "into the independent aggregate experiment after viewing test scores.</p>",
        "<h2>Independent aggregate models: mixed generalization</h2>"+table(metrics[metrics.selected]),
        "<p>The validation-selected combined-demand and Manhattan models underperform weekly naive in the holdout. "
        "Yellow Zone MSTL also underperforms with daily refitting while improving weekly forecasts. "
        "A validation win does not guarantee a test win.</p>",
        "<p>MAE and RMSE are pickups/hour at the named aggregation. WAPE is a percentage; MASE uses "
        "pre-test weekly differences. Do not compare these aggregate errors directly with Review 1 zone errors.</p>",
        "<h2>Model definitions</h2><p>MSTL-ETS decomposes log demand into 24-hour and 168-hour seasonality, "
        "then extrapolates the adjusted level using damped Holt exponential smoothing. Harmonic-AR uses ridge-fitted "
        "daily/weekly Fourier terms plus an AR(2) residual model; a separate variant adds calendar events. "
        "Daily SARIMA uses (1,0,1)(1,1,0)[7]. Simpler seasonal baselines remain eligible to win.</p>",
        "<h2>Uncertainty: observed coverage</h2>"+table(coverage),
        "<p>80% and 95% labels are nominal. Bands use held-out calibration errors grouped by lead. "
        "Dependent observations and winter demand shocks mean exact coverage is not guaranteed. These are marginal "
        "hourly intervals, not a simultaneous weekly path or a daily-total interval.</p>",
        "<h2>Zone-level forecasting</h2>"+table(pd.read_csv(TABLES/"zone_test_metrics.csv")),
        "<h2>Uncertainty for coherent aggregate forecasts</h2>"+table(pd.read_csv(TABLES/"bottom_up_interval_metrics.csv")),
        "<p>These bands are calibrated directly on summed zone forecast errors from the two pre-test weeks. "
        "They are not sums of independent zone intervals; intervals for different aggregate groups need not add up.</p>",
        "<p>Each zone selects weekly naive, a four-week seasonal mean, a damped level-adjusted seasonal mean, "
        "or TSB intermittent-demand smoothing on selection folds. Summing zones gives coherent aggregate forecasts. "
        "Independent aggregate models are reported separately.</p>",
        "<h2>Evidence and interpretation</h2>",
    ]
    for path in sorted(FIGURES.glob("*.png")):
        encoded=base64.b64encode(path.read_bytes()).decode()
        sections.append('<figure><img src="data:image/png;base64,'+encoded+'"><figcaption>'+html.escape(path.stem.replace("_"," "))+"</figcaption></figure>")
    sections.extend([
        "<h2>Limits that matter</h2><p>Six months cannot establish annual seasonality. Snow flags are retrospective "
        "diagnostic labels, never predictors. Observed pickups measure completed trips, not unmet demand or required fleet size. "
        "Holiday effects are associations based on few events. DST adjustment approximates a per-hour rate for the merged label; "
        "it cannot reconstruct the two lost physical timestamps. Test results are winter-specific. The March forecast is historical, "
        "unscored, and not a live October forecast.</p>",
        "<h2>Reproduce</h2><pre>pip install -r requirements.txt -r requirements-time-series.txt\n"
        "python scripts/test_time_series.py\npython scripts/run_time_series.py\npython scripts/validate_time_series.py</pre>",
        '<p>Methods: <a href="https://otexts.com/fpp3/dhr.html">Dynamic harmonic regression</a>; '
        '<a href="https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.MSTL.html">MSTL</a>; '
        '<a href="https://otexts.com/fpp3/tscv.html">Time-series cross-validation</a>. Full numeric evidence is in tables/.</p>'
    ])
    style="body{max-width:1120px;margin:50px auto;padding:0 24px;background:#f7f9fc;color:#263859;font:16px/1.65 system-ui}h1{font-size:48px;line-height:1.15}h1 span{font-size:25px;color:#1f6e8c}h2{margin-top:48px}table{display:block;overflow:auto;border-collapse:collapse;font-size:13px}td,th{padding:9px;border-bottom:1px solid #d6e0ea;text-align:right}th{background:#e5eef5}img{width:100%}figure{margin:35px 0}figcaption{color:#687c91;font-size:12px}pre{background:#e5eef5;padding:20px}"
    (OUT/"review_2_results.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Taxi demand | Review 2</title><style>'+style+"</style><body>"+"\n".join(sections)+"</body></html>",encoding="utf-8")
