# EDA Findings

Findings from the exploratory data analysis of the processed zone-hour demand table (`features.csv`, 138 zones, 8 Sep 2025 – 28 Feb 2026). Code: [`scripts/EDA_visuallization.ipynb`](../scripts/EDA_visuallization.ipynb). Charts: [`figures/`](figures/). Tables: [`tables/`](tables/).

Each finding uses the same format:

```
[ID] Short title
Finding:      what the data shows, with the key number(s)
Evidence:     figure or table name
Implication:  what this means for modelling, the dashboard or fleet planning
```

---

## Zone demand segmentation and predictability (#59)

**[C1] Zone ranking**
- **Finding:** Manhattan has 90.6% of the 21.7 M trips. The busiest zones are Upper East Side South (243 trips per hour), Midtown Center (221) and Upper East Side North (220). JFK Airport (202) is the only Queens zone in the top 10. The three island zones and Jamaica Bay have almost no pickups.
- **Evidence:** `C1_top_bottom_zones.png`
- **Implication:** Overall accuracy will be driven by a small set of Manhattan zones and JFK.

**[C2] Demand concentration**
- **Finding:** 16 of 138 zones (12%) make up half of all trips, and 33 zones (24%) make up 80%. The Gini coefficient is 0.71 overall: 0.49 within Manhattan and 0.84 within Queens.
- **Evidence:** `C2_pareto_chart.png`, `C2_lorenz_curve.png`
- **Implication:** Fleet coverage of about 30 zones serves most demand. Error metrics should be weighted by volume (for example WAPE), or the busy zones will be under-represented.

**[C6] Demand maps by time band**
- **Finding:** In the AM rush the residential Upper East and Upper West Side lead. At midday and PM rush, Midtown and JFK Airport join them. Late at night demand moves downtown to the East Village, West Village and Lower East Side. In the early morning (05–06) JFK Airport is the busiest zone.
- **Evidence:** `C6_demand_maps_by_time_band.png`
- **Implication:** The best place for taxis changes through the day. Zone × hour interaction matters for the model and the dashboard.

**[C7] Zone demand tiers**
- **Finding:** 39 High zones (37 in Manhattan) carry 86.7% of trips and almost never have a zero hour. 40 Near-empty zones (32 in Queens) carry 0.3% of trips and have zero trips in 74% of hours.
- **Evidence:** `C7_zone_tiers.png`, `tables/zone_tiers.csv`
- **Implication:** Treat near-empty zones separately or leave them out of zone-level models.

**[C8] Zone clusters by weekly demand profile**
- **Finding:** Three zone types (k = 3, best silhouette score of 0.30):
  - **Core business and airports (daytime):** 58 zones, 84.3% of trips. Demand builds through the day and peaks in the afternoon and early evening.
  - **Nightlife (late night and weekends):** 10 zones, 10.7% of trips. Small on weekdays, with very large peaks on Friday and Saturday nights.
  - **Residential (morning commute):** 30 zones, 4.8% of trips. Sharp weekday peak at 07–09, mostly upper Manhattan and Queens neighbourhoods.
- **Evidence:** `C8_choosing_k.png`, `C8_cluster_weekly_profiles.png`, `C8_cluster_map.png`, `tables/zone_clusters.csv`
- **Implication:** Use the cluster as a model feature, or train one model per zone type.

**[C10] Demand correlation between zones**
- **Finding:** Zones in the same cluster move together (average correlation 0.75), much more than zones in different clusters (0.38).
- **Evidence:** `C10_zone_correlation_heatmap.png`
- **Implication:** Zones of the same type can share information in a model, which helps quieter zones.

**[H1] Variability per zone**
- **Finding:** Busy zones are more stable relative to their size (median CV of about 0.7) than quiet zones (Near-empty median CV of 1.93). Among busy zones, the nightlife zones (Lower East Side, Greenwich Village South, East Village) are the most variable.
- **Evidence:** `H1_cv_vs_mean.png`
- **Implication:** Expect larger relative errors in nightlife and quiet zones.

**[H2] Demand pattern classes (Syntetos–Boylan)**
- **Finding:** 46 zones are Smooth, 35 Erratic, 43 Intermittent and 12 Lumpy (2 have no demand). Every High and Medium zone is Smooth or Erratic. Almost all Near-empty zones (36 of 40) are Intermittent.
- **Evidence:** `H2_demand_classes.png`, `tables/zone_tiers.csv`
- **Implication:** Standard count models suit busy zones. Intermittent zones need a zero-aware approach, or should be grouped together.

**[H6] Predictability by hour and weekday**
- **Finding:** Weekday daytime is the most predictable (CV of about 0.08–0.10 for Tuesday–Friday, 10:00–18:00). Late nights are the least predictable, especially early Friday and Saturday (CV up to 0.4). Mondays and Sundays vary more than mid-week days. Queens varies more than Manhattan (average slot CV of 0.25 vs 0.21).
- **Evidence:** `H6_predictability_heatmap.png`
- **Implication:** Report forecast accuracy by time band. Late-night and Queens forecasts will be less reliable.

---

## Demand over time and anomalies (#60)

**[D1] Hourly demand over the whole period**
- **Finding:** 5,203 trips per hour on average. The busiest hour was Friday 12 Dec at 18:00 (12,648 trips). The quietest was 23 Feb at 04:00 (87 trips), during a snowstorm. Every day follows the same strong daily cycle, and Queens is spikier than Manhattan because of the airports.
- **Evidence:** `D1_hourly_demand.png`
- **Implication:** Hour of day is the strongest calendar signal. Borough-level series behave differently.

**[D2] Daily demand, trend and calendar view**
- **Finding:** Demand falls by about 1,270 trips per day each week. The last 4 weeks are 15% below the first 4 (112.8 k vs 132.7 k trips per day). The deepest dips are Thanksgiving, Christmas to New Year and the snowstorms on 25 Jan and 23 Feb. The peak is mid-December (150–170 k per day). Thursday to Saturday are the busiest days.
- **Evidence:** `D2_daily_demand_trend.png`, `D2_calendar_heatmap.png`
- **Implication:** A random train/test split would mix seasons. A time-based split should expect lower winter levels in the test period.

**[D7] Hour x weekday heatmap**
- **Finding:** The busiest slot is Thursday 18:00 (10,770 trips per hour) and the quietest is Tuesday 03:00 (280). Between 00:00 and 03:00, Saturday and Sunday average 5,521 trips per hour vs 1,175 on Monday to Thursday (4.7 times as many). Queens peaks on Friday at 16:00.
- **Evidence:** `D7_hour_weekday_heatmap.png`
- **Implication:** The model needs the hour × weekday interaction, not hour and weekday separately.

**[E5] Anomaly days**
- **Finding:** 18 of 174 days are anomalies, and all are explained. The 13 low days are holidays and the days around them (Thanksgiving weekend, 24 Dec to 3 Jan) and snowstorms. The biggest drops are 23 Feb (-78%, 14 cm of snow), 25 Jan (-62%, 19 cm of snow) and Christmas Day (-58%). The 5 high days are in the pre-Christmas busy period (10–19 Dec, 26–32% above normal).
- **Evidence:** `E5_anomaly_days.png`
- **Implication:** Add flags for the holiday periods (not just the federal holiday dates) and for snow days.

**[E6] Zone-level spikes**
- **Finding:** 738 zone-hours in 73 zones are spikes (at least 3 times normal and at least 30 extra trips). They cluster on New Year's night (219 spike hours), Halloween night (89 on 1 Nov) and Thanksgiving, mostly between 00:00 and 03:00. The airports have 15% of spikes (LaGuardia 70). Event venues such as Penn Station / Madison Sq West and Lincoln Square East spike repeatedly.
- **Evidence:** `E6_zone_spikes.png`
- **Implication:** These surges cannot be predicted from current features. An event calendar or special-night flags would help.

**[E7] The daylight saving (DST) hour**
- **Finding:** The DST hour (2 Nov, 01:00) has 9,166 trips, 51% more than a normal Sunday 01:00 (6,084). For the median zone it is 1.71 times normal. The same value is copied into `trip_count_lag_24h` on 3 Nov 01:00 and `trip_count_lag_168h` on 9 Nov 01:00.
- **Evidence:** `E7_dst_hour.png`
- **Implication:** Flag this hour, or replace it and its two lag copies with a normal value, before modelling.

**[B6] The 50 busiest zone-hours**
- **Finding:** 44 of the top 50 are East Village on Saturday and Sunday nights at 00:00–01:00 (up to 1,122 trips), and 6 are Midtown Center on weekday evenings at 20:00–21:00. They repeat week after week, so they are real demand, not data errors.
- **Evidence:** `B6_top50_zone_hours.png`
- **Implication:** No outlier removal is needed. The extreme values are real nightlife peaks.

---

## Weather impact on demand (#61)

Method: **demand ratio** = actual trips / average trips of dry hours for the same zone, hour, weekday/weekend and month (holidays, the DST hour and near-empty zones are left out).

**[F1] Weather overview**
- **Finding:** Rain in 5.3% and snow in 2.5% of zone-hours. Feels-like temperature ranges from -25 to 32 °C, and snow only falls from December to February.
- **Evidence:** `F1_weather_overview.png`

**[F2] Rain and snow events**
- **Finding:** 68 wet events (59 rain, 9 snow). The biggest snowstorms were 22–23 Feb (23 cm) and 25 Jan (19 cm). The heaviest rain event was 19 Dec (32 mm).
- **Evidence:** `F2_weather_timeline.png`

**[F3] Weather correlation and forecast reliability**
- **Finding:** The forecast is well calibrated: at 71–100% it rains or snows in 95% of hours, and at 0–10% in 0.2%. Snowfall and forecast probability are correlated (r = 0.57).
- **Evidence:** `F3_weather_correlation_reliability.png`
- **Implication:** Forecast probability is a usable input for forecasts made a day ahead.

**[F4] Weather spread across zones**
- **Finding:** In 57% of rainy hours some zones stay dry. Temperature differs by about 2 °C across zones in the same hour.
- **Evidence:** `F4_weather_spread.png`
- **Implication:** Keep per-zone weather rather than one citywide value.

**[F5] Rain effect**
- **Finding:** Rain raises demand by about 5% (light) to 14% (> 5 mm per hour). The difference is significant (Mann–Whitney p < 0.001), but the effect size is small (0.14).
- **Evidence:** `F5_rain_effect.png`
- **Implication:** Keep `rain`. An intensity band feature may help.

**[F6] Snow effect**
- **Finding:** Light snow (≤ 0.2 cm per hour) has no effect. Heavier snow cuts pickups by 25% to 75%, and demand returns to normal 1–2 days after a big storm. Part of the drop is likely fewer taxis on the road, not only fewer riders.
- **Evidence:** `F6_snow_effect.png`
- **Implication:** `snowfall` is the most important weather feature. Add a snow-day / day-after-snow flag.

**[F7] Temperature effect**
- **Finding:** Almost no effect once hour, weekday and month are taken into account (all bands within ±3%).
- **Evidence:** `F7_temperature_effect.png`
- **Implication:** Temperature adds little beyond the calendar features.

**[F8] Forecast effect**
- **Finding:** Weak and mixed. Dry hours with a 51–70% forecast are 9% busier, and the other bands show no clear pattern.
- **Evidence:** `F8_forecast_effect.png`

**[F9] Weather by time of day**
- **Finding:** Rain matters most in the morning (early morning +19%, AM rush +15%) and slightly lowers evening demand (-5%). Snow hits evenings hardest (-57%).
- **Evidence:** `F9_weather_by_time.png`
- **Implication:** Weather × hour interactions matter. Tree-based models can capture them.

**[F10] Weather by place**
- **Finding:** In rain, residential Queens zones (Astoria, Sunnyside, Long Island City, about +25%) and Times Square rise most, the airports barely change (+1%), and Seaport and the Financial District fall. In snow, the airports drop most (-60%).
- **Evidence:** `F10_rain_sensitivity_by_zone.png`

**[F11] Before, during and after rain**
- **Finding:** Demand rises 1 hour before rain (+5%), peaks in the first rain hour (+7%) and returns to normal about 3 hours after the rain stops.
- **Evidence:** `F11_rain_timing.png`
- **Implication:** A "rain in the last 1–2 hours" feature may help.

**[F12] Extreme weather days**
- **Finding:** The heaviest rain day (30 Oct) was close to normal. The biggest snow day (25 Jan) was 62–68% below normal. The coldest day (8 Feb) was 10% above normal, with evening peaks that likely match Super Bowl Sunday.
- **Evidence:** `F12_extreme_weather_days.png`

**[I7] Weather effect summary**
- **Finding:** Snow, especially heavy snow, is by far the strongest weather effect (-30% to -70%). Rain adds +5% to +20% in the morning and rush hours. Very cold dry hours are close to normal.
- **Evidence:** `I7_weather_effect_summary.png`, `tables/weather_effects.csv`

---

## Feature relationships and correlations (#62)

**[A4] Validation of lag and rolling features**
- **Finding:** All 5 lag and rolling features match values recomputed from `trip_count` exactly (0 mismatches). A rolling mean that wrongly included the current hour would differ in 436 k rows.
- **Implication:** The engineered features are correct and have no data leakage.

**[G1] Correlation with `trip_count`**
- **Finding:** Lags have the strongest link with demand (r = 0.91–0.96). Hour has r = 0.20 (0.30 in Manhattan). Weather and the other calendar features are close to 0 as straight-line correlations, because their effects are relative changes hidden by the large size differences between zones.
- **Evidence:** `G1_feature_correlations.png`

**[G2] Lag relationships**
- **Finding:** On a log scale the relationship is roughly linear for busy zone-hours and noisy for small counts. `lag_1h` is the tightest and `roll_24h` the loosest.
- **Evidence:** `G2_lag_hexbin.png`
- **Implication:** A log transform of the target suits linear models.

**[G3] Lag correlation by zone tier**
- **Finding:** Median correlation with `lag_1h` is 0.90 for High zones, 0.79 for Medium, 0.44 for Low and 0.15 for Near-empty zones.
- **Evidence:** `G3_zone_lag_correlation.png`
- **Implication:** Lags work for busy zones only. Quiet zones need other inputs or grouping.

**[G4] Multicollinearity**
- **Finding:** `lag_1h` (VIF 28) and `roll_3h` (VIF 20) overlap strongly (r = 0.97). With only the 3 lags, every VIF is below 8.
- **Evidence:** `G4_multicollinearity.png`
- **Implication:** Linear models should drop `roll_3h`. Tree models can keep all features.

**[G5] Variance explained by categorical features**
- **Finding:** The zone alone explains 55% of the variance, and zone × hour explains 84%. Hour alone explains 6%. Weekday, month, weekend and holiday each explain under 1% on their own.
- **Evidence:** `G5_eta_squared.png`
- **Implication:** Zone identity (or zone tier / cluster) is essential. Calendar effects matter as interactions with zone and hour.

**[G6] Mutual information ranking**
- **Finding:** Ranking: lag_168h, lag_1h, lag_24h, roll_3h, zone ID, roll_24h, then hour. Weather and calendar features carry little information on their own.
- **Evidence:** `G6_mutual_information.png`
- **Implication:** Weather and calendar features adjust demand rather than set its level. Judge their value by model performance with and without them.
