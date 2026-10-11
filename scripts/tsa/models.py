"""Forecast dispatch and classical statistical models."""
import warnings
import numpy as np
from statsmodels.tsa.seasonal import MSTL
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from .baselines import seasonal_naive,seasonal_mean,adaptive_week
from .harmonic import harmonic_forecast

def hourly_forecast(name,history,train_calendar,future_calendar):
    y=np.asarray(history,dtype=float); h=len(future_calendar)
    if name=="naive_24": return seasonal_naive(y,h,24)
    if name=="naive_168": return seasonal_naive(y,h,168)
    if name=="mean_4weeks": return seasonal_mean(y,h)
    if name=="adaptive_week": return adaptive_week(y,h)
    if name.startswith("harmonic_ar"):
        return harmonic_forecast(y,train_calendar,future_calendar,events=name.endswith("_calendar"))
    if name=="mstl_ets":
        result=MSTL(np.log1p(y[-2016:]),periods=(24,168),stl_kwargs={"robust":True}).fit()
        seasonal=np.asarray(result.seasonal)
        adjusted=np.asarray(result.trend)+np.asarray(result.resid)
        fit=ExponentialSmoothing(adjusted,trend="add",damped_trend=True,initialization_method="estimated").fit()
        pred=fit.forecast(h)
        for j,period in enumerate((24,168)):
            pred=pred+seasonal[-period:,j][np.arange(h)%period]
        return np.maximum(np.expm1(pred),0)
    raise ValueError(name)

def daily_forecast(name,history,horizon):
    y=np.asarray(history,dtype=float)
    if name=="naive_7": return seasonal_naive(y,horizon,7)
    if name=="ets_weekly":
        fit=ExponentialSmoothing(np.log1p(y),trend="add",damped_trend=True,seasonal="add",
                                 seasonal_periods=7,initialization_method="estimated").fit()
        return np.maximum(np.expm1(fit.forecast(horizon)),0)
    if name=="sarima_weekly":
        fit=SARIMAX(np.log1p(y),order=(1,0,1),seasonal_order=(1,1,0,7),trend="n",
                    enforce_stationarity=True,enforce_invertibility=True).fit(disp=False,maxiter=200)
        if not fit.mle_retvals.get("converged",False):
            raise ValueError("SARIMA optimization did not converge")
        return np.maximum(np.expm1(fit.forecast(horizon)),0)
    raise ValueError(name)

def checked_forecast(call):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        prediction=np.asarray(call(),dtype=float)
    if not np.isfinite(prediction).all() or (prediction<0).any():
        raise ValueError("Nonfinite or negative prediction")
    # Optimization failures must disqualify a candidate, not silently pass.
    fatal=[w for w in caught if w.category.__name__=="ConvergenceWarning"]
    if fatal: raise ValueError(" | ".join(str(w.message) for w in fatal))
    return prediction," | ".join(dict.fromkeys(str(w.message) for w in caught))

