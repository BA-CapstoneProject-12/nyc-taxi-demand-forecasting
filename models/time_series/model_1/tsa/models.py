"""Forecast dispatch: seasonal profiles, without Fourier, ARIMA, or ETS fits."""
import warnings
import numpy as np
from .baselines import seasonal_naive,seasonal_mean,adaptive_week,adaptive_week_daily

def hourly_forecast(name,history,train_calendar,future_calendar):
    # Calendar contents deliberately do not enter these demand-profile forecasts.
    y=np.asarray(history,dtype=float); h=len(future_calendar)
    if name=="naive_24": return seasonal_naive(y,h,24)
    if name=="naive_168": return seasonal_naive(y,h,168)
    if name=="mean_4weeks": return seasonal_mean(y,h)
    if name=="adaptive_week": return adaptive_week(y,h)
    raise ValueError(name)

def daily_forecast(name,history,horizon):
    y=np.asarray(history,dtype=float)
    if name=="naive_7": return seasonal_naive(y,horizon,7)
    if name=="mean_4weeks_daily": return seasonal_mean(y,horizon,period=7)
    if name=="adaptive_week_daily": return adaptive_week_daily(y,horizon)
    raise ValueError(name)

def checked_forecast(call):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        prediction=np.asarray(call(),dtype=float)
    if not np.isfinite(prediction).all() or (prediction<0).any():
        raise ValueError("Nonfinite or negative prediction")
    fatal=[w for w in caught if w.category.__name__=="ConvergenceWarning"]
    if fatal: raise ValueError(" | ".join(str(w.message) for w in fatal))
    return prediction," | ".join(dict.fromkeys(str(w.message) for w in caught))
