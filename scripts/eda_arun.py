"""Reproducible Review 1 EDA for ArunN2005 (issues 63--66).

Run from any directory: python scripts/eda_arun.py --issues 63
Inputs are read only; outputs go exclusively to EDA_doc/.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "EDA_doc"
FIGURES = OUT / "figures"
TABLES = OUT / "tables"
DST = pd.Timestamp("2025-11-02 01:00")
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
# Recurring US federal calendar holidays used by the upstream feature pipeline.
# Source: https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/
HOLIDAYS = {
    "2025-09-01": "Labor Day", "2025-10-13": "Columbus Day",
    "2025-11-11": "Veterans Day", "2025-11-27": "Thanksgiving Day",
    "2025-12-25": "Christmas Day", "2026-01-01": "New Year's Day",
    "2026-01-19": "Martin Luther King Jr. Day", "2026-02-16": "Washington's Birthday",
}
COLORS = {"Manhattan": "#2878ad", "Queens": "#e78632",
          "Yellow Zone": "#d2a900", "Boro Zone": "#27836a", "Airports": "#9056a0"}
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 150,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .18, "font.size": 10})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGURES / name, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def table(frame, name, index=False):
    frame.to_csv(TABLES / name, index=index, float_format="%.8g")


def md_table(frame, columns=None, limit=None):
    """Small Markdown tables without an optional tabulate dependency."""
    if columns:
        frame = frame[columns]
    if limit:
        frame = frame.head(limit)
    rows = []
    for row in frame.itertuples(index=False, name=None):
        rows.append("| " + " | ".join(str(x).replace("|", "/") for x in row) + " |")
    return "| " + " | ".join(map(str, frame.columns)) + " |\n|" + "---|" * len(frame.columns) + "\n" + "\n".join(rows)


def finding(code, title, text, evidence, implication):
    links = []
    for file in evidence:
        folder = "figures" if file.endswith(".png") else "tables"
        links.append(f"[{file}]({folder}/{file})")
    return (f"\n**[{code}] {title}**\n\n- **Finding:** {text}\n"
            f"- **Evidence:** {', '.join(links)}\n- **Implication:** {implication}\n")


def write_section(issue, title, content):
    path = OUT / "EDA_findings.md"
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = """# EDA Findings

ArunN2005's Review 1 EDA for issues #63--#66. Reproduce with
`python scripts/eda_arun.py` or the companion `scripts/EDA_Arun.ipynb`.
Inputs: `data/processed/features.csv` and the existing zone/weather lookup files.
Analysis covers **8 Sep 2025 to 28 Feb 2026**, 174 complete local calendar days,
138 zones and 4,176 recorded hour labels per zone. Counts combine yellow and green
taxi pickups; `service_zone` describes an area, not a taxi fleet.

Zero counts are retained. All timestamps are naive New York local time. The
repeated 01:00 on 2 Nov 2025 combines two physical hours; rates here use recorded
hour labels unless explicitly stated. Partial weeks and September's missing first
week are labelled. Observed pickups measure completed service, not unmet rider
demand or required fleet size. Descriptive comparisons do not establish causation.

The other team EDA lives on its own branch; this file contains only Arun's assigned
IDs. Generated sections can be rerun without replacing unrelated sections.
"""
    start, end = f"<!-- arun-issue-{issue}:start -->", f"<!-- arun-issue-{issue}:end -->"
    block = f"{start}\n\n## {title} (#{issue})\n{content}\n{end}"
    pattern = re.escape(start) + r".*?" + re.escape(end)
    if re.search(pattern, text, flags=re.S):
        text = re.sub(pattern, lambda _: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    path.write_text(text, encoding="utf-8")


def load_data():
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(ROOT / "data/processed/features.csv", parse_dates=["pickup_hour"])
    zones = pd.read_csv(ROOT / "data/raw/taxi_zones_manhattan_queens.csv")
    data = data.merge(zones, left_on="PULocationID", right_on="LocationID", how="left", validate="many_to_one")
    if data["Zone"].isna().any():
        raise ValueError("Unmatched pickup zones")
    data = data.sort_values(["PULocationID", "pickup_hour"]).reset_index(drop=True)
    data["date"] = data.pickup_hour.dt.normalize()
    data["year_month"] = data.pickup_hour.dt.to_period("M").astype(str)
    data["week_start"] = data.date - pd.to_timedelta(data.day_of_week, unit="D")
    return data, zones


def zone_stats(data):
    result = data.groupby("PULocationID").trip_count.agg(
        rows="size", total="sum", mean="mean", variance="var", maximum="max",
        zero_share=lambda x: x.eq(0).mean(), p95=lambda x: x.quantile(.95), p99=lambda x: x.quantile(.99))
    result["variance_mean_ratio"] = result.variance.div(result["mean"].replace(0, np.nan))
    return result.join(data.groupby("PULocationID")[["Zone", "Borough", "service_zone", "latitude", "longitude"]].first())


def issue63(data, zones):
    features = pd.read_csv(ROOT / "data/processed/features.csv", parse_dates=["pickup_hour"])
    columns = ["PULocationID", "pickup_hour", "trip_count", "apparent_temperature", "rain", "snowfall",
               "precipitation_probability", "hour", "day_of_week", "month", "is_weekend", "is_holiday",
               "trip_count_lag_1h", "trip_count_lag_24h", "trip_count_lag_168h", "trip_count_roll_3h", "trip_count_roll_24h"]
    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "passed": bool(ok), "detail": str(detail)})

    check("A1 schema and nulls", features.columns.tolist() == columns and not features.isna().any().any(), "17 expected columns; zero nulls")
    check("A2 unique zone-hours", not features.duplicated(["PULocationID", "pickup_hour"]).any(), f"{len(features):,} rows")
    hours = pd.date_range("2025-09-08", "2026-02-28 23:00", freq="h")
    sizes = features.groupby("PULocationID").size()
    check("A2 complete rectangular grid", set(features.PULocationID) == set(zones.LocationID)
          and len(features) == len(zones) * len(hours) and sizes.eq(len(hours)).all()
          and set(features.pickup_hour) == set(hours), "138 zones x 4,176 local hour labels = 576,288")
    ints = ["PULocationID", "trip_count", "precipitation_probability", "hour", "day_of_week", "month",
            "trip_count_lag_1h", "trip_count_lag_24h", "trip_count_lag_168h"]
    check("A1 numeric and Boolean types", all(pd.api.types.is_integer_dtype(features[c]) for c in ints)
          and all(pd.api.types.is_float_dtype(features[c]) for c in ["apparent_temperature", "rain", "snowfall", "trip_count_roll_3h", "trip_count_roll_24h"])
          and all(pd.api.types.is_bool_dtype(features[c]) for c in ["is_weekend", "is_holiday"]), "integer counts/calendar, float weather/rolling, Boolean flags")
    numeric = features.select_dtypes("number")
    check("A3 finite values", np.isfinite(numeric).all().all(), "all numeric fields finite")
    nonnegative = [c for c in numeric if c not in ["apparent_temperature"]]
    check("A3 count and weather ranges", (features[nonnegative] >= 0).all().all()
          and features.precipitation_probability.between(0, 100).all()
          and features.hour.between(0, 23).all() and features.day_of_week.between(0, 6).all()
          and features.month.isin([9, 10, 11, 12, 1, 2]).all(), "nonnegative counts/rain/snow; probability 0--100; calendar ranges valid")
    check("A3 calendar derivation", features.hour.eq(features.pickup_hour.dt.hour).all()
          and features.day_of_week.eq(features.pickup_hour.dt.dayofweek).all()
          and features.month.eq(features.pickup_hour.dt.month).all(), "matches pickup_hour")
    expected_holidays = features.pickup_hour.dt.strftime("%Y-%m-%d").isin(HOLIDAYS)
    check("A5 weekend and holiday flags", features.is_weekend.eq(features.day_of_week.ge(5)).all()
          and features.is_holiday.eq(expected_holidays).all(), f"{features.is_holiday.sum():,} holiday rows; 7 dates; Labor Day is in warm-up")
    for borough in ["Manhattan", "Queens"]:
        split = pd.read_csv(ROOT / f"data/processed/features_{borough.lower()}.csv", parse_dates=["pickup_hour"])
        expected = features.loc[features.PULocationID.isin(zones.loc[zones.Borough.eq(borough), "LocationID"])]
        split = split.sort_values(["PULocationID", "pickup_hour"]).reset_index(drop=True)
        expected = expected.sort_values(["PULocationID", "pickup_hour"]).reset_index(drop=True)
        check(f"A6 {borough} exact split", split.equals(expected), f"{len(split):,} rows; all columns and values compared")
    report = (ROOT / "data/processed/cleaning_report.md").read_text(encoding="utf-8")
    clean_total = int(re.search(r"Final clean rows:\*\* ([\d,]+)", report).group(1).replace(",", ""))
    retained = int(features.trip_count.sum())
    # These lags recover Sep 1--7 once each, rather than summing overlapping lags.
    first_week = features.loc[features.pickup_hour.lt(pd.Timestamp("2025-09-15"))]
    warmup = int(first_week.trip_count_lag_168h.sum())
    check("A7 trip reconciliation", retained + warmup == clean_total,
          f"{retained:,} retained + {warmup:,} warm-up = {clean_total:,} cleaned pickups")
    raw_total = int(re.search(r"\| Raw input \| -- \| ([\d,]+)", report).group(1).replace(",", ""))
    audit = pd.read_csv(ROOT / "data/raw/taxi_collection_summary.csv")
    check("A7 raw collection audit", int(audit.rows_kept.sum()) == raw_total, f"{raw_total:,} raw pickups; {raw_total-clean_total:,} removed")
    weather = pd.read_csv(ROOT / "data/raw/weather_hourly_by_zone.csv", parse_dates=["weather_hour"])
    weather_cols = ["apparent_temperature", "rain", "snowfall", "precipitation_probability"]
    joined = features.merge(weather, left_on=["PULocationID", "pickup_hour"], right_on=["LocationID", "weather_hour"],
                            how="left", validate="one_to_one", suffixes=("", "_weather"))
    check("A8 weather join integrity", all(np.allclose(joined[c], joined[c+"_weather"], atol=1e-5, rtol=1e-6) for c in weather_cols), "every retained zone-hour matches source weather")
    cells = weather[["LocationID", "grid_latitude", "grid_longitude", "grid_elevation_m"]].drop_duplicates()
    # Grid identity uses latitude/longitude. API elevation metadata can differ
    # for zone centroids in the same horizontal model cell.
    cell_groups = cells.groupby(["grid_latitude", "grid_longitude"]).agg(
        LocationID=("LocationID", list), elevation_min=("grid_elevation_m", "min"),
        elevation_max=("grid_elevation_m", "max")).reset_index()
    cell_groups["zone_count"] = cell_groups.LocationID.map(len)
    cell_groups["zone_ids"] = cell_groups.LocationID.map(lambda x: ",".join(map(str, sorted(x))))
    table(cell_groups.drop(columns="LocationID"), "A8_shared_weather_cells.csv")
    check("A8 stable grid assignment", len(cells) == len(zones), f"{len(cell_groups)} cells for {len(zones)} zones; max {cell_groups.zone_count.max()} zones/cell")
    dst_total = int(features.loc[features.pickup_hour.eq(DST), "trip_count"].sum())
    report_dst = int(re.search(r"([\d,]+) trips carry", report).group(1).replace(",", ""))
    check("A8 DST audit", dst_total == report_dst, f"{dst_total:,} pickups in combined 01:00 label")
    table(pd.DataFrame(checks), "A1_A8_data_checks.csv")
    table(pd.DataFrame({"column": features.columns, "dtype": features.dtypes.astype(str).values,
                        "nulls": features.isna().sum().values}), "A1_schema.csv")
    table(numeric.agg(["min", "max"]).T.rename_axis("column").reset_index(), "A3_value_ranges.csv")
    table(pd.DataFrame({"stage": ["Raw", "Removed in cleaning", "Clean", "Warm-up (recovered from 168h lag)", "Retained features"],
                        "trips": [raw_total, raw_total-clean_total, clean_total, warmup, retained]}), "A7_trip_reconciliation.csv")
    failures = [c for c in checks if not c["passed"]]
    if failures:
        raise ValueError(f"Data checks failed: {failures}")

    stats = zone_stats(data)
    table(stats.reset_index(), "B4_zone_distribution.csv")
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.bar(range(len(sizes)), sizes.values, color=[COLORS[zones.set_index("LocationID").loc[x, "Borough"]] for x in sizes.index])
    ax.axhline(len(hours), color="black", linestyle="--", label="Expected 4,176")
    ticks = np.arange(0, len(sizes), 7)
    ax.set_xticks(ticks, sizes.index[ticks], rotation=90)
    ax.set(xlabel="Pickup zone ID (all 138 zones)", ylabel="Rows", title="A2 | Every zone retains the same 4,176 hour labels")
    ax.legend(); save(fig, "A2_rows_per_zone.png")
    zeros = data.assign(zero=data.trip_count.eq(0)).pivot_table(index="PULocationID", columns="date", values="zero", aggfunc="sum")
    table(zeros.rename_axis("PULocationID").reset_index(), "A2_zero_hours_by_zone_date.csv")
    fig, ax = plt.subplots(figsize=(14, 8))
    im = ax.imshow(zeros, aspect="auto", interpolation="nearest", vmin=0, vmax=24, cmap="magma")
    xt = np.arange(0, len(zeros.columns), 14); yt = np.arange(0, len(zeros), 7)
    ax.set_xticks(xt, [zeros.columns[i].strftime("%d %b") for i in xt], rotation=45)
    ax.set_yticks(yt, zeros.index[yt]); ax.set(xlabel="Local date", ylabel="Pickup zone ID", title="A2 | Zero-demand hour labels by zone and date")
    fig.colorbar(im, ax=ax, label="Zero hours per day (0--24)"); save(fig, "A2_zero_hour_heatmap.png")
    sundays = pd.to_datetime(["2025-10-19", "2025-10-26", "2025-11-02", "2025-11-09", "2025-11-16"])
    dst_compare = data.loc[data.date.isin(sundays)].groupby(["date", "hour"]).trip_count.sum().unstack("date")
    table(dst_compare.reset_index(), "A8_dst_comparison.csv")
    normal_01 = dst_compare.loc[1].drop(pd.Timestamp("2025-11-02")).mean()
    fig, ax = plt.subplots(figsize=(11, 4))
    for date in sundays:
        ax.plot(dst_compare.index, dst_compare[date], label=date.strftime("%d %b"), linewidth=2.5 if date.day == 2 else 1.2)
    ax.axvspan(.7, 1.3, color="red", alpha=.12)
    ax.set(xlabel="Local hour", ylabel="Trips across 138 zones", title="A8 | DST Sunday: two physical 01:00 hours share one label")
    ax.legend(ncol=5); save(fig, "A8_dst_comparison.png")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].hist(data.trip_count, bins=80, color="#2878ad"); axes[0].set(xlabel="Trips per zone-hour", ylabel="Zone-hours", title="Linear target")
    axes[1].hist(np.log1p(data.trip_count), bins=60, color="#27836a"); axes[1].set(xlabel="log(1 + trips)", ylabel="Zone-hours", title="Zero-preserving log transform")
    fig.suptitle("B1/B5 | Highly skewed pickup-count distribution"); save(fig, "B1_B5_target_histograms.png")
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for col, row in [("Borough", 0), ("service_zone", 1)]:
        names = sorted(data[col].unique())
        groups = [np.log1p(data.loc[data[col].eq(n), "trip_count"].to_numpy()) for n in names]
        axes[row, 0].boxplot(groups, tick_labels=names, showfliers=False)
        rng = np.random.default_rng(2005)
        sampled = [rng.choice(g, min(8000, len(g)), replace=False) for g in groups]
        axes[row, 1].violinplot(sampled, showmedians=True)
        axes[row, 1].set_xticks(range(1, len(names)+1), names)
        for ax in axes[row]: ax.set_ylabel("log(1 + trips per zone-hour)")
    axes[0, 0].set_title("Box: all rows; outlier dots hidden")
    axes[0, 1].set_title("Violin: <=8,000 sampled rows/group; seed 2005")
    fig.suptitle("B3 | Target shapes by borough and service area"); save(fig, "B3_borough_service_shapes.png")
    fig, ax = plt.subplots(figsize=(10, 4))
    for label, group in [("All", data), *list(data.groupby("Borough"))]:
        values, counts = np.unique(group.trip_count, return_counts=True)
        ax.step(np.log1p(values), np.cumsum(counts)/len(group), where="post", label=label)
    ax.set(xlabel="log(1 + trips per zone-hour)", ylabel="Cumulative fraction", title="B1/B3 | ECDF retains the zero-count mass")
    ax.legend(); save(fig, "B1_B3_ecdf.png")
    zero_hour = data.assign(zero=data.trip_count.eq(0)).groupby(["hour", "Borough"]).zero.mean().unstack()
    table(zero_hour.reset_index(), "B2_zero_share_by_hour.csv")
    fig, ax = plt.subplots(figsize=(12, 4)); (zero_hour * 100).plot.bar(ax=ax, color=COLORS)
    ax.set(xlabel="Local hour", ylabel="Zero zone-hours (%)", title="B2 | Zero-demand prevalence by hour and borough")
    save(fig, "B2_zero_share_by_hour.png")
    fig, ax = plt.subplots(figsize=(8, 5))
    positive = stats.loc[stats["mean"].gt(0)]
    for borough, group in positive.groupby("Borough"):
        ax.scatter(group["mean"], group.variance, label=borough, color=COLORS[borough], alpha=.75)
    bounds = np.geomspace(positive["mean"].min(), positive["mean"].max(), 100)
    ax.plot(bounds, bounds, "k--", label="Poisson: variance = mean")
    ax.set(xscale="log", yscale="log", xlabel="Mean pickups / zone-hour", ylabel="Sample variance", title="B4 | Pooled zone counts are overdispersed")
    ax.legend(); save(fig, "B4_mean_variance.png")
    summary = data.groupby("Borough").trip_count.agg(rows="size", total="sum", mean="mean", median="median", zero_share=lambda x: x.eq(0).mean())
    table(summary.reset_index(), "B3_borough_distribution.csv")
    quiet = stats.loc[stats["mean"].lt(1)].sort_values("total")
    table(quiet.reset_index(), "A8_near_empty_zones.csv")
    content = f"""
All **{len(checks)} checks pass**. No missing values or duplicate zone-hours; both borough
files exactly match their combined-file subsets (all 17 columns). The schema, finite
values, integer/Boolean types, calendar derivations, ranges and source-weather joins
were checked before any downstream analysis. Expected temperature limits are reported,
not clipped to the raw-data range: the retained period differs from the raw period.
Holiday validation follows the upstream recurring federal calendar definition, rather
than adding separate government closure days. [Calendar reference](https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/).

{md_table(pd.DataFrame(checks))}
"""
    content += finding("A1/A2/A3", "Schema, coverage and ranges", f"{len(features):,} rows across 138 zones, with exactly 4,176 rows per zone. All expected local hour labels are present; zero counts are observations.",
                       ["A1_schema.csv", "A3_value_ranges.csv", "A2_rows_per_zone.png", "A2_zero_hour_heatmap.png"], "Use the complete grid; dropping zeros would bias averages and temporal profiles.")
    content += finding("A5/A6", "Flags and borough splits", f"Weekend flags match Saturday/Sunday; {features.is_holiday.sum():,} rows cover seven federal holiday dates. Each borough has 69 zones and 288,144 rows.",
                       ["A1_A8_data_checks.csv"], "Labor Day is absent because Sep 1--7 was removed for lag warm-up; service area must not be interpreted as taxi type.")
    content += finding("A7", "Clean-trip reconciliation", f"{retained:,} retained trips + {warmup:,} warm-up trips = {clean_total:,} cleaned trips exactly. Warm-up demand was recovered once from lag_168h in Sep 8--14; these rows refer to Sep 1--7. Raw audit = {raw_total:,}; cleaning removed {raw_total-clean_total:,}.",
                       ["A7_trip_reconciliation.csv"], "Use retained-period totals for EDA; a direct comparison with all six months of cleaned trips would appear to lose demand.")
    content += finding("A8", "DST, sparse zones and weather cells", f"DST 01:00 has {dst_total:,} trips versus {normal_01:,.0f} on four nearby normal Sundays ({dst_total/normal_01:.2f}x, not an assumed 2x). There are {len(quiet)} zones with mean <1 pickup/hour; zones 103 and 104 are entirely zero. The 138 zones use {len(cell_groups)} weather cells, with up to {cell_groups.zone_count.max()} zones sharing a cell.",
                       ["A8_dst_comparison.png", "A8_near_empty_zones.csv", "A8_shared_weather_cells.csv"], "Do not remove sparse areas as errors. Flag DST and its lag copies; nearby Sundays differ in events/weather, and the marathon also occurs on DST day. Grid identity uses latitude/longitude; elevation metadata varies within some cells, so shared cells do not guarantee identical weather values and are not independent spatial observations.")
    content += finding("B1/B2/B3/B5", "Target distribution and zero prevalence", f"Mean={data.trip_count.mean():.2f}, median={data.trip_count.median():.0f}, maximum={data.trip_count.max():,}; {data.trip_count.eq(0).mean():.1%} of zone-hours are zero. Manhattan zero share={summary.loc['Manhattan','zero_share']:.1%}; Queens={summary.loc['Queens','zero_share']:.1%}. log1p compresses the tail while preserving zeros.",
                       ["B1_B5_target_histograms.png", "B3_borough_service_shapes.png", "B1_B3_ecdf.png", "B2_zero_share_by_hour.png", "B3_borough_distribution.csv"], "Compare count-based and zero-aware approaches. A log-target model needs retransformation validation; exp(prediction)-1 alone need not estimate the mean count.")
    content += finding("B4", "Overdispersion", f"{positive.variance.gt(positive['mean']).sum()} of {len(positive)} nonzero-demand zones have variance > mean; median variance/mean={positive.variance_mean_ratio.median():.2f}. All-zero zones have undefined variance/mean and are excluded from the log plot.",
                       ["B4_mean_variance.png", "B4_zone_distribution.csv"], "A constant-rate Poisson assumption is inadequate for pooled counts. Calendar/seasonal variation also contributes; this does not prove conditional overdispersion after modelling.")
    write_section(63, "Data checks and target distribution", content)
    print(f"#63: {len(checks)} checks passed; retained {retained:,} + warm-up {warmup:,} = clean {clean_total:,}.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issues", type=int, nargs="+", default=[63], choices=[63])
    args = parser.parse_args()
    data, zones = load_data()
    for issue in args.issues:
        {63: issue63}[issue](data, zones)


if __name__ == "__main__":
    main()
