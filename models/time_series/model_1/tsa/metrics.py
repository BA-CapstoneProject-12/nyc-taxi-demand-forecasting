"""Count-scale scores; zero-demand denominators remain explicitly undefined."""
import numpy as np

def scores(actual,prediction,history=None,season=168):
    y=np.asarray(actual,dtype=float); p=np.asarray(prediction,dtype=float)
    if y.shape != p.shape or y.size == 0 or not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError("Scores require aligned, finite, nonempty arrays")
    err=p-y
    denom=float(np.abs(y).sum())
    total=float(np.sum((y-y.mean())**2))
    result=dict(n=y.size,MAE=float(np.mean(np.abs(err))),RMSE=float(np.sqrt(np.mean(err**2))),
                WAPE=100*float(np.abs(err).sum())/denom if denom else np.nan,
                bias=float(err.mean()),R2=1-float(np.sum(err**2))/total if total else np.nan)
    if history is not None:
        history=np.asarray(history)
        scale=np.mean(np.abs(history[season:]-history[:-season])) if len(history)>season else 0
        result["MASE"]=result["MAE"]/scale if scale>0 else np.nan
    return result

def interval_scores(y,lo,hi,alpha):
    y=np.asarray(y);lo=np.asarray(lo);hi=np.asarray(hi)
    width=hi-lo
    penalty=2/alpha*((lo-y)*(y<lo)+(y-hi)*(y>hi))
    return dict(coverage=float(np.mean((y>=lo)&(y<=hi))),mean_width=float(width.mean()),
                interval_score=float(np.mean(width+penalty)))
