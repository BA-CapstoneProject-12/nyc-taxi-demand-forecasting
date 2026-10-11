"""Individual zone selection, intermittent demand, and coherent bottom-up totals."""
import numpy as np
import pandas as pd
from .config import TABLES,TARGET,ZONE_MODELS,SELECTION_FOLDS
from .baselines import seasonal_naive,seasonal_mean,adaptive_week,tsb
from .metrics import scores

def forecast_panel(name,history,horizon):
    if name=="naive_168": return seasonal_naive(history,horizon,168)
    if name=="mean_4weeks": return seasonal_mean(history,horizon)
    if name=="adaptive_week": return adaptive_week(history,horizon)
    if name=="tsb": return tsb(history,horizon)
    raise ValueError(name)

def run_zones(calendar,zones,profile,folds):
    panel=zones.pivot(index="ds",columns="PULocationID",values=TARGET).sort_index()
    cv=[]
    for fold in folds.itertuples():
        history=panel.loc[:fold.train_end].to_numpy()
        actual=panel.loc[fold.forecast_start:fold.forecast_end].to_numpy()
        for name in ZONE_MODELS:
            pred=forecast_panel(name,history,len(actual))
            mae=np.mean(np.abs(actual-pred),axis=0)
            cv.extend(dict(PULocationID=int(z),model=name,fold=fold.fold,MAE=e)
                      for z,e in zip(panel.columns,mae))
    cv=pd.DataFrame(cv);cv.to_csv(TABLES/"zone_cv_metrics.csv",index=False)
    selection=cv[cv.fold.isin(SELECTION_FOLDS)].groupby(["PULocationID","model"],sort=False).MAE.mean().reset_index()
    selected=selection.loc[selection.groupby("PULocationID").MAE.idxmin()].set_index("PULocationID").reindex(panel.columns)
    selected.join(profile[["Zone","Borough","volume_tier","demand_pattern"]]).to_csv(TABLES/"zone_selection.csv")
    test=calendar.index[calendar.split.eq("test")];parts=[]
    for schedule in (24,168):
        for origin in pd.date_range(test[0],test[-1],freq=f"{schedule}h"):
            future=panel.loc[origin:min(origin+pd.Timedelta(hours=schedule-1),test[-1])]
            history=panel.loc[panel.index<origin].to_numpy()
            preds={name:forecast_panel(name,history,len(future)) for name in ZONE_MODELS}
            chosen=np.column_stack([preds[name][:,j] for j,name in enumerate(selected.model)])
            n=len(future);nz=len(panel.columns)
            parts.append(pd.DataFrame(dict(ds=np.repeat(future.index,nz),PULocationID=np.tile(panel.columns,n),
                          actual=future.to_numpy().ravel(),prediction=chosen.ravel(),baseline=preds["naive_168"].ravel(),
                          model=np.tile(selected.model.to_numpy(),n),origin=origin,schedule=schedule,
                          lead=np.repeat(np.arange(1,n+1),nz))))
    result=pd.concat(parts,ignore_index=True)
    result.to_csv(TABLES/"zone_predictions.csv.gz",index=False,float_format="%.7g")
    byzone=[];summary=[];groups=[];coherent=[]
    for schedule,p in result.groupby("schedule"):
        for col in ("prediction","baseline"):
            summary.append(dict(schedule=schedule,model="selected_zone_models" if col=="prediction" else "naive_168",
                                **scores(p.actual,p[col])))
        for zone,g in p.groupby("PULocationID"):
            history=panel.loc[panel.index<test[0],zone].to_numpy()
            byzone.append(dict(schedule=schedule,PULocationID=zone,model=selected.loc[zone,"model"],
                               baseline_MAE=np.mean(abs(g.actual-g.baseline)),**scores(g.actual,g.prediction,history)))
        named=p.merge(profile[["Borough","service_zone","volume_tier","demand_pattern"]],left_on="PULocationID",right_index=True,validate="many_to_one")
        for attribute in ("Borough","volume_tier","demand_pattern"):
            for label,g in named.groupby(attribute):
                groups.append(dict(schedule=schedule,group_type=attribute,group=label,
                                   baseline_MAE=np.mean(abs(g.actual-g.baseline)),**scores(g.actual,g.prediction)))
        for attr in (None,"Borough","service_zone"):
            grouped=[("All zones",named)] if attr is None else named.groupby(attr)
            for label,g in grouped:
                totals=g.groupby(["ds","origin","lead"])[["actual","prediction","baseline"]].sum().reset_index()
                totals["series_id"]=label;totals["schedule"]=schedule;coherent.append(totals)
    pd.DataFrame(summary).to_csv(TABLES/"zone_test_metrics.csv",index=False)
    pd.DataFrame(byzone).merge(profile[["Zone","Borough","volume_tier","demand_pattern"]],left_on="PULocationID",right_index=True).to_csv(TABLES/"zone_error_analysis.csv",index=False)
    pd.DataFrame(groups).to_csv(TABLES/"zone_group_metrics.csv",index=False)
    coherent=pd.concat(coherent,ignore_index=True)
    coherent.to_csv(TABLES/"bottom_up_predictions.csv.gz",index=False,float_format="%.8g")
    rows=[]
    for (sid,schedule),g in coherent.groupby(["series_id","schedule"]):
        rows.append(dict(series_id=sid,schedule=schedule,**scores(g.actual,g.prediction)))
    pd.DataFrame(rows).to_csv(TABLES/"bottom_up_metrics.csv",index=False)
    # Calibrate the coherent aggregate forecasts on the same held-out weeks.
    # Model choices are already locked by folds 1-4; no test residuals are used.
    from .intervals import calibrate
    calibration=[]
    start=folds.loc[folds.fold.eq(5),"forecast_start"].iloc[0]
    end=folds.loc[folds.fold.eq(6),"forecast_end"].iloc[0]
    group_ids={"All zones":list(panel.columns)}
    for attr in ("Borough","service_zone"):
        group_ids.update({str(label):list(g.index) for label,g in profile.groupby(attr)})
    for schedule in (24,168):
        for origin in pd.date_range(start,end,freq=f"{schedule}h"):
            future=panel.loc[origin:min(origin+pd.Timedelta(hours=schedule-1),end)]
            history=panel.loc[panel.index<origin].to_numpy()
            preds={name:forecast_panel(name,history,len(future)) for name in ZONE_MODELS}
            chosen=np.column_stack([preds[name][:,j] for j,name in enumerate(selected.model)])
            forecasts=pd.DataFrame(chosen,index=future.index,columns=panel.columns)
            for sid,ids in group_ids.items():
                calibration.append(pd.DataFrame(dict(ds=future.index,actual=future[ids].sum(axis=1).to_numpy(),
                    prediction=forecasts[ids].sum(axis=1).to_numpy(),series_id=sid,model="bottom_up",
                    origin=origin,phase="calibration",schedule=schedule,lead=np.arange(1,len(future)+1))))
    cal=pd.concat(calibration,ignore_index=True)
    cal.to_csv(TABLES/"bottom_up_calibration_predictions.csv.gz",index=False,float_format="%.8g")
    evaluated=coherent.copy()
    evaluated["phase"]="test";evaluated["model"]="bottom_up"
    calibrate(pd.concat([cal,evaluated],ignore_index=True),dict.fromkeys(group_ids,"bottom_up"),prefix="bottom_up_")
    # Historical deployment example issued just after the final observed hour.
    index=pd.date_range(panel.index[-1]+pd.Timedelta(hours=1),periods=168,freq="h")
    preds={name:forecast_panel(name,panel.to_numpy(),168) for name in ZONE_MODELS}
    future=np.column_stack([preds[name][:,j] for j,name in enumerate(selected.model)])
    pd.DataFrame(future,index=index,columns=panel.columns).rename_axis("ds").to_csv(TABLES/"zone_forecast_next_week.csv",float_format="%.5f")
    print("Zone forecasts complete: 138 zones, daily and weekly origins",flush=True)
    return result
