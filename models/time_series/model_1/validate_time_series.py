"""Independent checks on saved outputs, timestamps, metrics, and input hashes."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
from tsa.config import ROOT,TABLES,FIGURES,SERIES,OUT

def validate():
    checks=[]
    def check(name,condition):
        checks.append(dict(check=name,passed=bool(condition)))
        if not condition: raise AssertionError(name)
    manifest=pd.read_csv(TABLES/"input_manifest.csv")
    for row in manifest.itertuples():
        check("unchanged input "+row.path,hashlib.sha256((ROOT/row.path).read_bytes()).hexdigest()==row.sha256)
    check("input checks all pass",pd.read_csv(TABLES/"input_checks.csv").passed.all())
    p=pd.read_csv(TABLES/"hourly_predictions.csv.gz",parse_dates=["ds","origin"])
    check("forecast timestamps respect origins",(p.ds>=p.origin).all())
    check("hourly lead matches issue time",((p.ds-p.origin)/pd.Timedelta(hours=1)+1).eq(p.lead).all())
    check("lead is inside issued horizon",(p.lead<=p.schedule).all())
    check("predictions finite nonnegative",np.isfinite(p.prediction).all() and p.prediction.ge(0).all())
    check("prediction keys unique",not p.duplicated(["series_id","model","schedule","origin","ds"]).any())
    test=p[p.phase.eq("test")]
    expected=pd.date_range("2026-01-25 04:00","2026-02-28 23:00",freq="h")
    truth=pd.read_csv(ROOT/"data/processed/time_series/ts_aggregate_hourly.csv",parse_dates=["ds"])
    truth=truth.set_index(["series_id","ds"]).trip_count_adj
    metrics=pd.read_csv(TABLES/"hourly_test_metrics.csv")
    selected=json.loads((TABLES/"hourly_selected.json").read_text())
    for (sid,model,schedule),g in test.groupby(["series_id","model","schedule"]):
        key=f"{sid}/{model}/{schedule}"
        check("exact test timestamps "+key,pd.DatetimeIndex(g.sort_values("ds").ds).equals(expected))
        target=truth.loc[pd.MultiIndex.from_arrays([g.series_id,g.ds])].to_numpy()
        check("test targets match source "+key,np.allclose(target,g.actual))
        row=metrics[metrics.series_id.eq(sid)&metrics.model.eq(model)&metrics.schedule.eq(schedule)].iloc[0]
        check("independent MAE "+key,np.isclose(np.mean(abs(g.actual-g.prediction)),row.MAE,rtol=1e-6))
        check("independent RMSE "+key,np.isclose(np.sqrt(np.mean((g.actual-g.prediction)**2)),row.RMSE,rtol=1e-6))
    for sid,name in selected.items():
        selection=pd.read_csv(TABLES/"hourly_selection.csv")
        rows=selection[selection.series_id.eq(sid)&selection.eligible]
        check("selection follows CV "+sid,rows.loc[rows.selection_MAE.idxmin(),"model"]==name)
    radii=pd.read_csv(TABLES/"interval_calibration.csv",parse_dates=["calibration_end"])
    check("all calibration before test",radii.calibration_end.lt(expected[0]).all())
    check("two weekly calibration origins",radii[radii.schedule.eq(168)].calibration_origins.eq(2).all())
    bands=pd.read_csv(TABLES/"hourly_intervals.csv.gz")
    check("one interval per selected test timestamp",len(bands)==6*2*836)
    for level in (80,95):
        check("ordered bounds "+str(level),(bands["lower_"+str(level)]<=bands.prediction).all() and (bands.prediction<=bands["upper_"+str(level)]).all())
        check("nonnegative lower bound "+str(level),bands["lower_"+str(level)].ge(0).all())
    check("nested intervals",(bands.lower_95<=bands.lower_80).all() and (bands.upper_95>=bands.upper_80).all())
    interval_metrics=pd.read_csv(TABLES/"interval_metrics.csv")
    for row in interval_metrics.itertuples():
        g=bands[bands.series_id.eq(row.series_id)&bands.schedule.eq(row.schedule)]
        suffix=str(round(row.nominal_coverage*100))
        empirical=np.mean((g.actual>=g["lower_"+suffix])&(g.actual<=g["upper_"+suffix]))
        check(f"independent interval coverage {row.series_id}/{row.schedule}/{suffix}",np.isclose(empirical,row.coverage))
    zones=pd.read_csv(TABLES/"zone_predictions.csv.gz",parse_dates=["ds","origin"])
    check("complete zone predictions",len(zones)==2*836*138)
    check("unique zone forecast keys",not zones.duplicated(["PULocationID","ds","schedule"]).any())
    check("zone origin boundaries",(zones.ds>=zones.origin).all())
    check("zone forecasts nonnegative",zones.prediction.ge(0).all() and np.isfinite(zones.prediction).all())
    zm=pd.read_csv(TABLES/"zone_test_metrics.csv")
    for row in zm.itertuples():
        g=zones[zones.schedule.eq(row.schedule)]
        col="prediction" if row.model=="selected_zone_models" else "baseline"
        check(f"independent zone MAE {row.schedule}/{row.model}",np.isclose(np.mean(abs(g.actual-g[col])),row.MAE,rtol=1e-6))
    bottom=pd.read_csv(TABLES/"bottom_up_predictions.csv.gz")
    for schedule in (24,168):
        b=bottom[bottom.schedule.eq(schedule)].pivot(index="ds",columns="series_id",values="prediction")
        check("borough coherence "+str(schedule),np.allclose(b["All zones"],b.Manhattan+b.Queens,rtol=1e-6))
        check("service coherence "+str(schedule),np.allclose(b["All zones"],b["Yellow Zone"]+b["Boro Zone"]+b.Airports,rtol=1e-6))
    daily=pd.read_csv(TABLES/"daily_predictions.csv",parse_dates=["ds","origin"])
    check("daily forecasts are issued before outcomes",(daily.ds>=daily.origin).all())
    for key,g in daily.groupby(["series_id","model"]):
        check("daily holdout "+str(key),pd.DatetimeIndex(g.sort_values("ds").ds).equals(pd.date_range("2026-01-25","2026-02-28")))
    future=pd.read_csv(TABLES/"aggregate_forecast_next_week.csv",parse_dates=["ds","origin"])
    check("next week coverage",len(future)==6*168 and future.ds.min()==pd.Timestamp("2026-03-01") and future.ds.max()==pd.Timestamp("2026-03-07 23:00"))
    check("future outputs no fabricated actuals","actual" not in future.columns)
    coherent_bands=pd.read_csv(TABLES/"bottom_up_hourly_intervals.csv.gz")
    coherent_cal=pd.read_csv(TABLES/"bottom_up_interval_calibration.csv",parse_dates=["calibration_end"])
    check("coherent calibration precedes test",coherent_cal.calibration_end.lt(expected[0]).all())
    check("coherent interval coverage grid",len(coherent_bands)==6*2*836)
    check("coherent intervals nested",(coherent_bands.lower_95<=coherent_bands.lower_80).all() and (coherent_bands.upper_95>=coherent_bands.upper_80).all())
    for row in pd.read_csv(TABLES/"bottom_up_interval_metrics.csv").itertuples():
        g=coherent_bands[coherent_bands.series_id.eq(row.series_id)&coherent_bands.schedule.eq(row.schedule)]
        suffix=str(round(row.nominal_coverage*100))
        measured=((g.actual>=g["lower_"+suffix])&(g.actual<=g["upper_"+suffix])).mean()
        check(f"coherent interval coverage {row.series_id}/{row.schedule}/{suffix}",np.isclose(measured,row.coverage))
    for path in FIGURES.glob("*.png"):
        with Image.open(path) as image:
            check("readable figure "+path.name,min(image.size)>500)
            image.verify()
    check("thirteen review figures",len(list(FIGURES.glob("*.png")))==13)
    check("Model 1 forecast implementation exists",(OUT/"tsa/models.py").is_file() and (OUT/"tsa/baselines.py").is_file())
    check("Model 1 notebook exists",(OUT/"time_series_analysis1.ipynb").is_file())
    check("report remains outside repository",not (OUT/"review_2_results.pdf").exists() and not (OUT/"review_2_results.html").exists())
    allowed_hourly={"naive_24","naive_168","mean_4weeks","adaptive_week"}
    allowed_daily={"naive_7","mean_4weeks_daily","adaptive_week_daily"}
    for name in ("hourly_selection.csv","hourly_fit_log.csv","hourly_fold_metrics.csv","hourly_cv_predictions.csv.gz","hourly_predictions.csv.gz"):
        check("only distinct hourly models "+name,set(pd.read_csv(TABLES/name).model)<=allowed_hourly)
    for name in ("daily_selection.csv","daily_fit_log.csv","daily_cv_predictions.csv","daily_predictions.csv"):
        check("only distinct daily models "+name,set(pd.read_csv(TABLES/name).model)<=allowed_daily)
    check("overlapping source retired",not (OUT/"tsa/harmonic.py").exists())
    for name in ("models.py","diagnostics.py"):
        import ast
        tree=ast.parse((OUT/"tsa"/name).read_text(encoding="utf-8-sig"))
        imported={alias.name for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom)) for alias in node.names}
        check("no overlapping model imports "+name,not imported.intersection({"MSTL","SARIMAX","ExponentialSmoothing","AutoReg"}))
    pd.DataFrame(checks).to_csv(TABLES/"output_checks.csv",index=False)
    print(f"Output validation: {len(checks)} checks passed")
    return checks

if __name__=="__main__":validate()
