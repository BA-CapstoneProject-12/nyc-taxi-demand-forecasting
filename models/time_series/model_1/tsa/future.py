"""Historical next-week forecast issued on 1 March 2026, not a live forecast."""
import json
import numpy as np
import pandas as pd
from .config import TABLES,TARGET
from .models import hourly_forecast,checked_forecast
from .intervals import lead_bucket

def next_week(calendar,hourly):
    selected=json.loads((TABLES/"hourly_selected.json").read_text())
    origin=calendar.index[-1]+pd.Timedelta(hours=1)
    future=pd.DataFrame(index=pd.date_range(origin,periods=168,freq="h"))
    # Only future timestamps and horizon length are used by profile forecasts.
    # This is a historical extrapolation, with no future weather or event inputs.
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
