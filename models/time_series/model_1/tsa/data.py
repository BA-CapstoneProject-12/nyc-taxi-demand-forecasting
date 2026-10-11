"""Input reconciliation and source-data checks."""
import hashlib
import numpy as np
import pandas as pd
from .config import ROOT, DATA, TABLES, TARGET, SERIES, ensure_output

def load_inputs():
    calendar = pd.read_csv(DATA / "ts_calendar_hourly.csv", parse_dates=["ds"]).set_index("ds")
    hourly = pd.read_csv(DATA / "ts_aggregate_hourly.csv", parse_dates=["ds"])
    daily = pd.read_csv(DATA / "ts_aggregate_daily.csv", parse_dates=["date"])
    zones = pd.read_csv(DATA / "ts_zone_hourly.csv", parse_dates=["ds"])
    profile = pd.read_csv(DATA / "ts_zone_profile.csv").set_index("PULocationID")
    folds = pd.read_csv(DATA / "ts_cv_folds.csv", parse_dates=[
        "train_start", "train_end", "forecast_start", "forecast_end"])
    return calendar, hourly, daily, zones, profile, folds

def audit():
    ensure_output()
    calendar, hourly, daily, zones, profile, folds = load_inputs()
    rows = []
    def check(name, condition, detail):
        rows.append(dict(check=name, passed=bool(condition), detail=str(detail)))
    times = calendar.index
    check("complete hourly calendar", times.equals(pd.date_range(times.min(), times.max(), freq="h")), len(times))
    check("fixed study window", len(times) == 4344 and str(times[0]) == "2025-09-01 00:00:00", times[-1])
    check("zone keys unique", not zones.duplicated(["PULocationID", "ds"]).any(), len(zones))
    panel = zones.pivot(index="ds", columns="PULocationID", values=TARGET).sort_index()
    check("complete zone grid", panel.shape == (4344, 138) and panel.notna().all().all(), panel.shape)
    check("nonnegative finite target", np.isfinite(panel).all().all() and (panel >= 0).all().all(), TARGET)
    check("all aggregate series", set(hourly.series_id) == set(SERIES), hourly.series_id.unique())
    for sid, frame in hourly.groupby("series_id"):
        frame = frame.sort_values("ds")
        check("regular " + sid, pd.DatetimeIndex(frame.ds).equals(times), len(frame))
        ids = profile.index if sid == "All zones" else profile.index[
            profile.Borough.eq(sid) | profile.service_zone.eq(sid)]
        actual = frame.set_index("ds")[TARGET]
        check("zone reconciliation " + sid, np.allclose(panel[ids].sum(axis=1), actual), len(ids))
        by_day = frame.groupby(frame.ds.dt.normalize())[[TARGET, "trip_count"]].sum()
        saved = daily[daily.series_id.eq(sid)].set_index("date")[[TARGET, "trip_count"]]
        check("daily reconciliation " + sid, np.allclose(by_day, saved.reindex(by_day.index)), len(saved))
    zone_daily = pd.read_csv(DATA / "ts_zone_daily.csv", parse_dates=["date"])
    zd = zones.assign(date=zones.ds.dt.normalize()).groupby(["PULocationID", "date"])[[TARGET, "trip_count"]].sum()
    zd_saved = zone_daily.set_index(["PULocationID", "date"])[[TARGET, "trip_count"]].reindex(zd.index)
    check("zone daily reconciliation", np.allclose(zd, zd_saved), len(zd))
    check("clean trip total", zones.trip_count.sum() == 22579793, zones.trip_count.sum())
    dst = zones.ds.eq(pd.Timestamp("2025-11-02 01:00"))
    check("DST correction confined to repeated label", np.allclose(zones.loc[~dst,TARGET], zones.loc[~dst,"trip_count"])
          and np.allclose(zones.loc[dst,TARGET]*2, zones.loc[dst,"trip_count"]), dst.sum())
    check("profile keys", set(profile.index) == set(panel.columns), len(profile))
    check("split sizes", calendar.groupby("split").size().to_dict() == {"train":3172,"validation":336,"test":836}, calendar.groupby("split").size().to_dict())
    test_times = times[calendar.split.eq("test")]
    ml = pd.read_csv(ROOT / "models/modeling/test.csv", usecols=["PULocationID","pickup_hour","trip_count"], parse_dates=["pickup_hour"])
    ts_test = zones[zones.ds.isin(test_times)].rename(columns={"ds":"pickup_hour"})
    paired = ts_test.merge(ml, on=["PULocationID","pickup_hour"], validate="one_to_one", suffixes=("_tsa","_ml"))
    check("Review 1 test targets match", len(paired) == 115368 and paired.trip_count_tsa.eq(paired.trip_count_ml).all(), len(paired))
    check("folds before test", folds.forecast_end.lt(test_times[0]).all(), folds.forecast_end.max())
    check("fold boundaries", (folds.train_end + pd.Timedelta(hours=1)).eq(folds.forecast_start).all()
          and ((folds.forecast_end-folds.forecast_start)/pd.Timedelta(hours=1)+1).eq(168).all(), len(folds))
    manifest=[]
    for path in sorted(DATA.glob("*.csv")):
        frame=pd.read_csv(path)
        check("finite numeric " + path.name, not np.isinf(frame.select_dtypes(include="number")).any().any(), frame.shape)
        manifest.append(dict(path=path.relative_to(ROOT).as_posix(),rows=len(frame),columns=len(frame.columns),
                             bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    pd.DataFrame(manifest).to_csv(TABLES/"input_manifest.csv",index=False)
    checks=pd.DataFrame(rows)
    checks.to_csv(TABLES/"input_checks.csv",index=False)
    if not checks.passed.all():
        raise ValueError(checks[~checks.passed].to_string(index=False))
    print(f"Input audit: {len(checks)} checks passed",flush=True)
    return calendar,hourly,daily,zones,profile,folds
