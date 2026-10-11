"""Two-stage dynamic harmonic regression, with short-memory AR(2) errors.

This is explicitly a ridge regression followed by an AR error fit, not joint
maximum-likelihood SARIMAX. Calendar terms are the only future regressors.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from statsmodels.tsa.ar_model import AutoReg
from .config import EVENT_FEATURES

EPOCH=pd.Timestamp("2025-09-01")
def design(calendar,events=True):
    t=(pd.DatetimeIndex(calendar.index)-EPOCH)/pd.Timedelta(hours=1)
    cols={}
    for period,kmax,label in ((24,6,"day"),(168,16,"week")):
        for k in range(1,kmax+1):
            if period==168 and k%7==0: continue
            cols[f"{label}_sin_{k}"]=np.sin(2*np.pi*k*t/period)
            cols[f"{label}_cos_{k}"]=np.cos(2*np.pi*k*t/period)
    if events:
        for name in EVENT_FEATURES:
            cols[name]=calendar[name].astype(float).to_numpy()
    return pd.DataFrame(cols,index=calendar.index)

def harmonic_forecast(history,train_calendar,future_calendar,events=True):
    # Local fitting adapts seasonal shape while retaining enough weekly cycles.
    y=np.log1p(np.asarray(history)[-2016:])
    x=design(train_calendar.iloc[-len(y):],events)
    xf=design(future_calendar,events)
    weight=np.power(.5,np.arange(len(y)-1,-1,-1)/1008)
    regression=Ridge(alpha=3).fit(x,y,sample_weight=weight)
    residual=y-regression.predict(x)
    ar=AutoReg(residual,lags=2,trend="n",old_names=False).fit()
    correction=ar.predict(start=len(y),end=len(y)+len(xf)-1)
    prediction=np.maximum(np.expm1(regression.predict(xf)+correction),0)
    if not np.isfinite(prediction).all():
        raise ValueError("Harmonic model produced invalid forecasts")
    return prediction

