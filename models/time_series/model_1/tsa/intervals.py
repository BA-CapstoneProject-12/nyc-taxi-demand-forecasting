"""Pre-test residual calibration; dependent observations imply empirical bands.

These are horizon-binned marginal prediction intervals. They are not simultaneous
paths and do not have an exchangeability-based coverage guarantee for this series.
"""
import math
import numpy as np
import pandas as pd
from .config import TABLES
from .metrics import interval_scores

def lead_bucket(lead,schedule):
    lead=np.asarray(lead)
    return np.where(lead<=6,"01-06",np.where(lead<=12,"07-12","13-24")) if schedule==24 else np.where(lead<=24,"001-024",np.where(lead<=72,"025-072","073-168"))

def corrected_quantile(values,coverage):
    values=np.sort(np.asarray(values,dtype=float))
    if len(values)==0 or not np.isfinite(values).all(): raise ValueError("Invalid calibration scores")
    rank=min(len(values),math.ceil((len(values)+1)*coverage))
    return float(values[rank-1])

def calibrate(predictions,selected,prefix=""):
    selected_rows=predictions[predictions.apply(lambda r:r.model==selected[r.series_id],axis=1)].copy()
    selected_rows["bucket"]=""
    for schedule in (24,168):
        mask=selected_rows.schedule.eq(schedule)
        selected_rows.loc[mask,"bucket"]=lead_bucket(selected_rows.loc[mask,"lead"],schedule)
    calibration=selected_rows[selected_rows.phase.eq("calibration")]
    rows=[]
    for (sid,schedule,bucket),p in calibration.groupby(["series_id","schedule","bucket"]):
        error=np.abs(p.actual-p.prediction)
        for coverage in (.8,.95):
            rows.append(dict(series_id=sid,schedule=schedule,bucket=bucket,coverage=coverage,
                             radius=corrected_quantile(error,coverage),calibration_n=len(p),
                             calibration_origins=p.origin.nunique(),calibration_end=p.ds.max()))
    radii=pd.DataFrame(rows);radii.to_csv(TABLES/(prefix+"interval_calibration.csv"),index=False)
    test=selected_rows[selected_rows.phase.eq("test")].copy()
    metrics=[]
    for coverage in (.8,.95):
        rad=radii[radii.coverage.eq(coverage)].drop(columns=["coverage"])
        test=test.merge(rad[["series_id","schedule","bucket","radius"]],on=["series_id","schedule","bucket"],validate="many_to_one")
        suffix=str(int(coverage*100))
        test["lower_"+suffix]=np.maximum(0,test.prediction-test.radius)
        test["upper_"+suffix]=test.prediction+test.radius
        test=test.drop(columns="radius")
        for (sid,schedule),p in test.groupby(["series_id","schedule"]):
            metrics.append(dict(series_id=sid,schedule=schedule,nominal_coverage=coverage,
                                **interval_scores(p.actual,p["lower_"+suffix],p["upper_"+suffix],1-coverage)))
    test.to_csv(TABLES/(prefix+"hourly_intervals.csv.gz"),index=False,float_format="%.8g")
    pd.DataFrame(metrics).to_csv(TABLES/(prefix+"interval_metrics.csv"),index=False)
    return test

def block_bootstrap_comparison(predictions,selected,repetitions=2000):
    """Paired forecast-origin blocks, preserving within-block serial dependence."""
    rng=np.random.default_rng(42);rows=[]
    test=predictions[predictions.phase.eq("test")]
    for sid,name in selected.items():
        for schedule in (24,168):
            p=test[test.series_id.eq(sid)&test.schedule.eq(schedule)]
            chosen=p[p.model.eq(name)].copy()
            base=p[p.model.eq("naive_168")][["ds","origin","prediction"]].rename(columns={"prediction":"baseline"})
            chosen=chosen.merge(base,on=["ds","origin"],validate="one_to_one")
            chosen["improvement"]=abs(chosen.actual-chosen.baseline)-abs(chosen.actual-chosen.prediction)
            blocks=chosen.groupby("origin").improvement.agg(["sum","count"])
            indices=rng.integers(0,len(blocks),size=(repetitions,len(blocks)))
            samples=blocks["sum"].to_numpy()[indices].sum(axis=1)/blocks["count"].to_numpy()[indices].sum(axis=1)
            rows.append(dict(series_id=sid,schedule=schedule,MAE_improvement=chosen.improvement.mean(),
                             lower_95=np.quantile(samples,.025),upper_95=np.quantile(samples,.975),
                             origin_blocks=len(blocks),note="Exploratory; adjacent origins can remain dependent"))
    pd.DataFrame(rows).to_csv(TABLES/"paired_block_bootstrap.csv",index=False)
