"""Expanding-origin comparisons with selection locked before test evaluation."""
import json
import time
import numpy as np
import pandas as pd
from .config import (TABLES,TARGET,SERIES,HOURLY_MODELS,DAILY_MODELS,SELECTION_FOLDS)
from .models import hourly_forecast,daily_forecast,checked_forecast
from .metrics import scores

def prediction_frame(index,actual,prediction,sid,model,origin,phase,schedule,fold=0):
    return pd.DataFrame(dict(ds=index,actual=np.asarray(actual),prediction=prediction,
                             series_id=sid,model=model,origin=origin,phase=phase,
                             schedule=schedule,fold=fold,lead=np.arange(1,len(index)+1)))

def select_models(cv,candidates,frequency):
    rows=[]; selected={}
    for sid in SERIES:
        for name in candidates:
            p=cv[cv.series_id.eq(sid)&cv.model.eq(name)&cv.fold.isin(SELECTION_FOLDS)]
            eligible=p.fold.nunique()==4 and len(p)==(672 if frequency=="hourly" else 28)
            rows.append(dict(series_id=sid,model=name,eligible=eligible,
                             selection_MAE=np.mean(np.abs(p.actual-p.prediction)) if eligible else np.nan))
        eligible_rows=[r for r in rows if r["series_id"]==sid and r["eligible"]]
        if not eligible_rows: raise ValueError("No eligible model for "+sid)
        selected[sid]=min(eligible_rows,key=lambda r:r["selection_MAE"])["model"]
    pd.DataFrame(rows).to_csv(TABLES/f"{frequency}_selection.csv",index=False)
    (TABLES/f"{frequency}_selected.json").write_text(json.dumps(selected,indent=2)+"\n",encoding="utf-8")
    return selected

def run_hourly(calendar,hourly,folds):
    logs=[]; parts=[]
    for sid in SERIES:
        frame=hourly[hourly.series_id.eq(sid)].sort_values("ds").set_index("ds")
        y=frame[TARGET]
        for fold in folds.itertuples():
            train=y.loc[:fold.train_end]
            future=calendar.loc[fold.forecast_start:fold.forecast_end]
            for name in HOURLY_MODELS:
                start=time.perf_counter()
                try:
                    pred,warn=checked_forecast(lambda:hourly_forecast(name,train,calendar.loc[train.index],future))
                    parts.append(prediction_frame(future.index,y.loc[future.index],pred,sid,name,
                                                  future.index[0],"cv",168,fold.fold))
                    status="ok"
                except (ValueError,np.linalg.LinAlgError) as exc:
                    status="failed";warn=str(exc)
                logs.append(dict(series_id=sid,fold=fold.fold,model=name,status=status,warnings=warn,
                                 seconds=time.perf_counter()-start))
        print("Hourly CV complete: "+sid,flush=True)
    cv=pd.concat(parts,ignore_index=True)
    pd.DataFrame(logs).to_csv(TABLES/"hourly_fit_log.csv",index=False)
    selected=select_models(cv,HOURLY_MODELS,"hourly")
    cv.to_csv(TABLES/"hourly_cv_predictions.csv.gz",index=False,float_format="%.8g")
    # Selection is persisted before a single test prediction is scored.
    test=calendar.index[calendar.split.eq("test")]
    calibration_start=folds.loc[folds.fold.eq(5),"forecast_start"].iloc[0]
    calibration_end=folds.loc[folds.fold.eq(6),"forecast_end"].iloc[0]
    output=[]
    for sid in SERIES:
        frame=hourly[hourly.series_id.eq(sid)].sort_values("ds").set_index("ds")
        y=frame[TARGET]
        for schedule in (24,168):
            intervals=[("test",test[0],test[-1])]
            if schedule==24: intervals.insert(0,("calibration",calibration_start,calibration_end))
            for phase,start,end in intervals:
                for origin in pd.date_range(start,end,freq=f"{schedule}h"):
                    future=calendar.loc[origin:min(origin+pd.Timedelta(hours=schedule-1),end)]
                    history=y[y.index<origin]
                    for name in dict.fromkeys([selected[sid],"naive_168"]):
                        pred,warn=checked_forecast(lambda:hourly_forecast(name,history,calendar.loc[history.index],future))
                        output.append(prediction_frame(future.index,y.loc[future.index],pred,sid,name,origin,phase,schedule))
            if schedule==168:
                p=cv[cv.series_id.eq(sid)&cv.model.eq(selected[sid])&cv.fold.isin([5,6])].copy()
                p["phase"]="calibration";output.append(p)
        print("Hourly holdout complete: "+sid+" -> "+selected[sid],flush=True)
    output=pd.concat(output,ignore_index=True)
    output.to_csv(TABLES/"hourly_predictions.csv.gz",index=False,float_format="%.8g")
    metrics=[]
    for (sid,name,schedule),p in output[output.phase.eq("test")].groupby(["series_id","model","schedule"]):
        history=hourly[hourly.series_id.eq(sid)&hourly.ds.lt(test[0])][TARGET]
        metrics.append(dict(series_id=sid,model=name,schedule=schedule,selected=name==selected[sid],
                            **scores(p.actual,p.prediction,history)))
    pd.DataFrame(metrics).to_csv(TABLES/"hourly_test_metrics.csv",index=False)
    fold_metrics=[]
    for (sid,name,fold),p in cv.groupby(["series_id","model","fold"]):
        fold_metrics.append(dict(series_id=sid,model=name,fold=fold,
                                 role="selection" if fold in SELECTION_FOLDS else "calibration",
                                 **scores(p.actual,p.prediction)))
    pd.DataFrame(fold_metrics).to_csv(TABLES/"hourly_fold_metrics.csv",index=False)
    return selected,output

def run_daily(daily,folds):
    parts=[];logs=[]
    for sid in SERIES:
        y=daily[daily.series_id.eq(sid)].sort_values("date").set_index("date")[TARGET]
        for fold in folds.itertuples():
            origin=fold.forecast_start.normalize()
            index=pd.date_range(origin,periods=7,freq="D")
            history=y[y.index<origin]
            for name in DAILY_MODELS:
                try:
                    pred,warn=checked_forecast(lambda:daily_forecast(name,history,7))
                    parts.append(prediction_frame(index,y.loc[index],pred,sid,name,origin,"cv",7,fold.fold))
                    status="ok"
                except (ValueError,np.linalg.LinAlgError) as exc:
                    status="failed";warn=str(exc)
                logs.append(dict(series_id=sid,fold=fold.fold,model=name,status=status,warnings=warn))
    cv=pd.concat(parts,ignore_index=True)
    pd.DataFrame(logs).to_csv(TABLES/"daily_fit_log.csv",index=False)
    selected=select_models(cv,DAILY_MODELS,"daily")
    cv.to_csv(TABLES/"daily_cv_predictions.csv",index=False)
    parts=[];metrics=[]
    for sid in SERIES:
        frame=daily[daily.series_id.eq(sid)].sort_values("date").set_index("date")
        y=frame[TARGET];test=frame.index[frame.split.eq("test")]
        for origin in pd.date_range(test[0],test[-1],freq="7D"):
            index=pd.date_range(origin,min(origin+pd.Timedelta(days=6),test[-1]),freq="D")
            history=y[y.index<origin]
            for name in dict.fromkeys([selected[sid],"naive_7"]):
                pred,warn=checked_forecast(lambda:daily_forecast(name,history,len(index)))
                parts.append(prediction_frame(index,y.loc[index],pred,sid,name,origin,"test",7))
        print("Daily holdout complete: "+sid+" -> "+selected[sid],flush=True)
    predictions=pd.concat(parts,ignore_index=True)
    predictions.to_csv(TABLES/"daily_predictions.csv",index=False)
    for (sid,name),p in predictions.groupby(["series_id","model"]):
        history=daily[daily.series_id.eq(sid)&daily.date.lt(p.ds.min())][TARGET]
        metrics.append(dict(series_id=sid,model=name,selected=name==selected[sid],
                            **scores(p.actual,p.prediction,history,season=7)))
    pd.DataFrame(metrics).to_csv(TABLES/"daily_test_metrics.csv",index=False)
    return selected
