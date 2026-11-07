"""
Shared helpers for the dashboard: file paths, colours, page styling,
cached data loaders and the two forecasting models.
"""

import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DASHBOARD_DIR = Path(__file__).resolve().parent
REPO = DASHBOARD_DIR.parent
DATA = DASHBOARD_DIR / "data"
EDA_FIG = REPO / "EDA_doc" / "figures"
EDA_TAB = REPO / "EDA_doc" / "tables"
MODELING = REPO / "models" / "modeling"
TS_MODEL = REPO / "models" / "time_series" / "model_1"
TS_DATA = REPO / "data" / "processed" / "time_series"
ARM_FINDINGS = REPO / "data" / "processed" / "arm_findings"
ARM_PREP = REPO / "data" / "processed" / "association_rules"

# The team's time-series model code lives in models/time_series/model_1/tsa.
sys.path.insert(0, str(TS_MODEL))
from tsa.baselines import adaptive_week, seasonal_mean, seasonal_naive, tsb  # noqa: E402

# ---------------------------------------------------------------------------
# Colours (validated colour-blind-safe categorical order)
# ---------------------------------------------------------------------------
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
MAGENTA, GREEN, VIOLET, RED = "#e87ba4", "#008300", "#6250d6", "#e34948"
SERIES = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED]
GRAY = "#8a8984"
INK, INK_2, INK_3 = "#0b0b0b", "#52514e", "#8a8984"
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = [[0, "#d03b3b"], [0.5, "#f0efec"], [1, "#2a78d6"]]

# Fixed colours per entity so the same thing always has the same colour.
MODEL_COLORS = {
    "Naive 168-hour baseline": GRAY,
    "Linear Regression": BLUE,
    "Random Forest": AQUA,
    "HistGradientBoosting": ORANGE,
}
DEMAND_COLORS = {"High": ORANGE, "Medium": BLUE, "Low": AQUA}
CLUSTER_COLORS = {
    "Core business and airports (daytime)": BLUE,
    "Nightlife (late night and weekends)": ORANGE,
    "Residential (morning commute)": AQUA,
    "Near-empty (not clustered)": "#c3c2b7",
}

# Plotly template used by every chart.
pio.templates["taxi"] = go.layout.Template(
    layout=dict(
        colorway=SERIES,
        font=dict(family="Inter, -apple-system, Segoe UI, sans-serif", size=13, color=INK_2),
        title=dict(font=dict(size=15, color=INK), x=0, xanchor="left", y=1, yref="container", yanchor="top", pad=dict(t=10)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, linecolor="#d9d8d3", ticks="outside", tickcolor="#d9d8d3", zeroline=False, automargin=True),
        yaxis=dict(gridcolor="#ecebe7", zeroline=False, linecolor="rgba(0,0,0,0)", automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text=""),
        hoverlabel=dict(bgcolor="white", font_size=12, bordercolor="#d9d8d3"),
        margin=dict(l=10, r=10, t=80, b=10),
        bargap=0.25,
    )
)
pio.templates.default = "taxi"

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
TIME_BANDS = {
    "late_night": "Late night (00–04)",
    "early_morning": "Early morning (05–06)",
    "am_rush": "AM rush (07–09)",
    "midday": "Midday (10–15)",
    "pm_rush": "PM rush (16–19)",
    "evening": "Evening (20–23)",
}

# ---------------------------------------------------------------------------
# Page styling and small layout components
# ---------------------------------------------------------------------------
CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1250px;}
h1, h2, h3 {letter-spacing: -0.01em;}
.hero {
  background: linear-gradient(120deg, #0d366b 0%, #1c5cab 60%, #2a78d6 100%);
  color: white; border-radius: 14px; padding: 1.6rem 1.9rem; margin-bottom: 1.2rem;
}
.hero .kicker {text-transform: uppercase; font-size: 0.78rem; letter-spacing: .12em; opacity: .8;}
.hero h1 {color: white; margin: .2rem 0 .4rem 0; font-size: 2rem; padding: 0;}
.hero p {margin: 0; opacity: .92; font-size: 1.02rem; max-width: 900px;}
.kpi {
  border: 1px solid #e6e5e0; border-radius: 12px; padding: .9rem 1rem; background: #fcfcfb; height: 100%;
}
.kpi .label {font-size: .78rem; color: #52514e; text-transform: uppercase; letter-spacing: .06em;}
.kpi .value {font-size: 1.75rem; font-weight: 700; color: #0b0b0b; line-height: 1.25;}
.kpi .note {font-size: .82rem; color: #8a8984;}
.callout {
  border-left: 4px solid #2a78d6; background: #f3f7fd; padding: .8rem 1rem;
  border-radius: 6px; margin: .4rem 0 1rem 0; color: #1f1f1e;
}
.callout.use {border-left-color: #1baf7a; background: #f1faf6;}
.callout.warn {border-left-color: #eda100; background: #fdf8ec;}
.callout b {color: #0b0b0b;}
.step {
  border: 1px solid #e6e5e0; border-radius: 12px; padding: .9rem 1rem; background: white; height: 100%;
}
.step .num {
  display: inline-block; width: 1.7rem; height: 1.7rem; border-radius: 50%; background: #2a78d6;
  color: white; text-align: center; line-height: 1.7rem; font-weight: 700; font-size: .85rem; margin-bottom: .4rem;
}
.step .title {font-weight: 650; color: #0b0b0b; margin-bottom: .2rem;}
.step .body {font-size: .88rem; color: #52514e;}
.big-number {font-size: 3rem; font-weight: 800; color: #0b0b0b; line-height: 1.1;}
.pill {
  display: inline-block; padding: .15rem .6rem; border-radius: 999px; font-size: .8rem;
  font-weight: 600; margin-right: .3rem; border: 1px solid #d9d8d3; background: #f6f6f4; color: #1f1f1e;
}
</style>
"""


def apply_style():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(kicker, title, text):
    st.markdown(
        f'<div class="hero"><div class="kicker">{kicker}</div><h1>{title}</h1><p>{text}</p></div>',
        unsafe_allow_html=True,
    )


def kpi_row(items):
    """items: list of (label, value, note) tuples shown as cards in one row."""
    columns = st.columns(len(items))
    for column, (label, value, note) in zip(columns, items):
        column.markdown(
            f'<div class="kpi"><div class="label">{label}</div>'
            f'<div class="value">{value}</div><div class="note">{note}</div></div>',
            unsafe_allow_html=True,
        )


def callout(text, kind="info"):
    """kind: 'info' (blue), 'use' (green, how it helps users) or 'warn' (amber)."""
    css_class = {"info": "callout", "use": "callout use", "warn": "callout warn"}[kind]
    st.markdown(f'<div class="{css_class}">{text}</div>', unsafe_allow_html=True)


def steps(items):
    """items: list of (title, body) shown as numbered cards in one row."""
    columns = st.columns(len(items))
    for i, (column, (title, body)) in enumerate(zip(columns, items), start=1):
        column.markdown(
            f'<div class="step"><div class="num">{i}</div><div class="title">{title}</div>'
            f'<div class="body">{body}</div></div>',
            unsafe_allow_html=True,
        )


def show_chart(fig, height=None, toolbar=True):
    fig.update_layout(legend_title_text="")  # the chart title already names what is shown
    if height:
        fig.update_layout(height=height)
    st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False, "displayModeBar": toolbar})


def figure(path, caption):
    """Show one of the saved analysis figures from the repository."""
    if Path(path).exists():
        st.image(str(path), caption=caption, width="stretch")


def next_chapter(text):
    st.divider()
    st.caption(f"Next chapter → {text}")


# ---------------------------------------------------------------------------
# Cached data loaders
# ---------------------------------------------------------------------------
def check_data_built():
    if not (DATA / "zones.csv").exists():
        st.error("Dashboard data not found. Run `python dashboard/build_data.py` from the repository root first.")
        st.stop()


@st.cache_data
def read_csv(path, **kwargs):
    return pd.read_csv(path, **kwargs)


@st.cache_data
def load_zones():
    return pd.read_csv(DATA / "zones.csv").sort_values("Zone").reset_index(drop=True)


@st.cache_data
def load_features():
    """The final modelling table: one row per zone and hour (8 Sep 2025 - 28 Feb 2026)."""
    return pd.read_csv(REPO / "data" / "processed" / "features.csv", parse_dates=["pickup_hour"])


@st.cache_data
def load_test_predictions():
    return pd.read_csv(DATA / "test_predictions.csv", parse_dates=["pickup_hour"])


@st.cache_data
def load_zone_hourly():
    """Hourly pickups, one column per zone (column names are zone IDs as text)."""
    return pd.read_csv(DATA / "zone_hourly_wide.csv", index_col=0, parse_dates=True)


@st.cache_data
def load_aggregate_hourly():
    return pd.read_csv(DATA / "aggregate_hourly.csv", parse_dates=["ds"])


@st.cache_data
def load_zone_shapes():
    """Official taxi-zone outlines (saved by build_data.py)."""
    return json.loads((DATA / "taxi_zones.geojson").read_text())


def zone_map(frame, color, color_map=None, hover_data=None, order=None, title="", labels=None):
    """Draw the taxi zones as shapes coloured by one column. Needs no map tiles or internet."""
    fig = px.choropleth(
        frame, geojson=load_zone_shapes(), locations="PULocationID", featureidkey="properties.id",
        color=color, color_discrete_map=color_map, category_orders={color: order} if order else None,
        hover_name="Zone", hover_data=hover_data, title=title, labels=labels,
    )
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_traces(marker_line_color="white", marker_line_width=0.6)
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), dragmode=False)
    return fig


@st.cache_data
def load_rules():
    rules = pd.read_csv(ARM_FINDINGS / "arm_rules_final_non_redundant.csv")
    rules["demand"] = rules["consequent_text"].str.replace("demand=", "", regex=False)
    rules["conditions"] = rules["antecedent_text"].str.split(", ")
    return rules


# ---------------------------------------------------------------------------
# Model 3 (HistGradientBoosting) - the best prediction model from Review 1
# ---------------------------------------------------------------------------
MODEL_FEATURES = [
    "PULocationID", "hour", "day_of_week", "month",
    "apparent_temperature", "rain", "snowfall", "precipitation_probability", "is_holiday",
    "trip_count_lag_1h", "trip_count_lag_24h", "trip_count_lag_168h",
    "trip_count_roll_3h", "trip_count_roll_24h",
]


@st.cache_resource
def load_hgb_model():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # saved with scikit-learn 1.9.0; predictions are identical
        return joblib.load(MODELING / "model_3_hist_gradient_boosting.joblib")


def predict_demand(rows):
    """Predict hourly pickups for a DataFrame that has the 14 model features."""
    model = load_hgb_model()
    prediction = model.predict(rows[MODEL_FEATURES])
    return np.clip(prediction, 0, None)


@st.cache_data
def load_zone_normal():
    """Average pickups per zone for each weekday and hour in the training period (no holidays)."""
    return pd.read_csv(DATA / "zone_normal.csv")


LEVEL_MEANING = {"High": "busier than usual", "Medium": "about usual", "Low": "quieter than usual"}


def compare_with_normal(predicted, normal):
    """High / Medium / Low compared with the zone's normal demand for the same weekday and hour.
    Within ±15% of normal counts as Medium. Adding 1 to both sides stops near-empty zones
    from flipping on one or two pickups."""
    ratio = (predicted + 1) / (normal + 1)
    if ratio >= 1.15:
        return "High"
    if ratio <= 0.85:
        return "Low"
    return "Medium"


def demand_tier(value, zone_row):
    """Low / Medium / High compared with the zone's own training history (ARM terciles)."""
    if not zone_row["arm_active"]:
        return "Low"
    if value <= zone_row["q_low"]:
        return "Low"
    if value <= zone_row["q_high"]:
        return "Medium"
    return "High"


# ---------------------------------------------------------------------------
# Time-series Model 1 - the four forecasting methods (team code in tsa/)
# ---------------------------------------------------------------------------
METHOD_NAMES = {
    "adaptive_week": "Adaptive seasonal",
    "mean_4weeks": "Four-week mean",
    "tsb": "TSB (intermittent)",
    "naive_168": "Weekly naive",
}


def run_method(method, history, horizon):
    """Forecast `horizon` hours from a 1-D history array using one Model 1 method."""
    y = np.asarray(history, dtype=float)
    if method == "adaptive_week":
        return adaptive_week(y, horizon)
    if method == "mean_4weeks":
        return seasonal_mean(y, horizon)
    if method == "naive_168":
        return seasonal_naive(y, horizon, 168)
    if method == "tsb":
        return tsb(y, horizon)[:, 0]
    raise ValueError(method)


def forecast_bottom_up(zone_hourly, zones, origin, horizon, zone_ids=None):
    """Forecast every chosen zone with its selected method and add them up."""
    history = zone_hourly[zone_hourly.index < origin]
    method_of = dict(zip(zones["PULocationID"].astype(str), zones["ts_method"]))
    columns = zone_ids if zone_ids is not None else list(zone_hourly.columns)
    total = np.zeros(horizon)
    for zone_id in columns:
        total += run_method(method_of[zone_id], history[zone_id].values, horizon)
    return total


def lead_bucket(lead, horizon):
    """Lead-time groups used for the calibrated prediction intervals."""
    if horizon == 24:
        return "01-06" if lead <= 6 else ("07-12" if lead <= 12 else "13-24")
    return "001-024" if lead <= 24 else ("025-072" if lead <= 72 else "073-168")


# ---------------------------------------------------------------------------
# Association rules - plain-English wording
# ---------------------------------------------------------------------------
ITEM_TEXT = {
    "day_type=weekday": "weekday", "day_type=weekend": "weekend",
    "holiday=regular": "regular day", "holiday=federal": "federal holiday",
    "rain=no": "no rain", "rain=yes": "raining",
    "snow=no": "no snow", "snow=yes": "snowing",
    "temperature=lower": "cold (< −0.9 °C)", "temperature=middle": "mild (−0.9 to 9.9 °C)",
    "temperature=upper": "warmer (> 9.9 °C)",
    "zone_cluster=daytime": "daytime/business zone", "zone_cluster=morning_commute": "commuter zone",
    "zone_cluster=nightlife": "nightlife zone", "zone_cluster=near_empty": "near-empty zone",
}
for _key, _label in TIME_BANDS.items():
    ITEM_TEXT[f"time_band={_key}"] = _label


def describe_rule(conditions):
    """['time_band=am_rush', 'day_type=weekday'] -> 'AM rush (07–09) + weekday'"""
    return " + ".join(ITEM_TEXT.get(item, item) for item in conditions)
