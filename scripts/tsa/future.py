"""Historical next-week forecast issued on 1 March 2026, not a live forecast."""
import json
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from .config import TABLES,TARGET,EVENT_FEATURES
from .models import hourly_forecast,checked_forecast
from .intervals import lead_bucket

def next_week(calendar,hourly):
    selected=json.loads((TABLES/"hourly_selected.json").read_text())
    origin=calendar.index[-1]+pd.Timedelta(hours=1)
    future=pd.DataFrame(index=pd.date_range(origin,periods=168,freq="h"))
    # This export intentionally covers the fixed study's next week only.
    if origin != pd.Timestamp("2026-03-01"):
        raise ValueError("Review the event calendar before forecasting a different study window")
    holidays=USFederalHolidayCalendar().holidays(origin-pd.Timedelta(days=14),origin+pd.Timedelta(days=14))
    dates=future.index.normalize()
    for name in EVENT_FEATURES: future[name]=False
    future["is_holiday"]=dates.isin(holidays)
    future["is_day_before_holiday"]=(dates+pd.Timedelta(days=1)).isin(holidays)
    future["is_day_after_holiday"]=(dates-pd.Timedelta(days=1)).isin(holidays)
    radii=pd.read_csv(TABLES/"interval_calibration.csv")
    parts=[]
    for sid,name in selected.items():
        frame=hourly[hourly.series_id.eq(sid)].sort_values("ds").set_index("ds")
        pred,_=checked_forecast(lambda:hourly_forecast(name,frame[TARGET],calendar,future))
        p=pd.DataFrame(dict(ds=future.index,series_id=sid,model=name,origin=origin,prediction=pred,
                            lead=np.arange(1,169),bucket=lead_bucket(np.arange(1,169),168)))
        for coverage in (.8,.95):
            r=radii[radii.series_id.eq(sid)&radii.schedule.eq(168)&radii.coverage.eq(coverage)].set_index("bucket").radius
            radius=p.bucket.map(r)
            suffix=str(int(coverage*100))
            p["lower_"+suffix]=np.maximum(0,p.prediction-radius)
            p["upper_"+suffix]=p.prediction+radius
        parts.append(p)
    pd.concat(parts,ignore_index=True).to_csv(TABLES/"aggregate_forecast_next_week.csv",index=False,float_format="%.7g")
