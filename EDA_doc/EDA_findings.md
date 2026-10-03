# EDA Findings

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

<!-- arun-issue-63:start -->

## Data checks and target distribution (#63)

All **15 checks pass**. No missing values or duplicate zone-hours; both borough
files exactly match their combined-file subsets (all 17 columns). The schema, finite
values, integer/Boolean types, calendar derivations, ranges and source-weather joins
were checked before any downstream analysis. Expected temperature limits are reported,
not clipped to the raw-data range: the retained period differs from the raw period.
Holiday validation follows the upstream recurring federal calendar definition, rather
than adding separate government closure days. [Calendar reference](https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/).

| check | passed | detail |
|---|---|---|
| A1 schema and nulls | True | 17 expected columns; zero nulls |
| A2 unique zone-hours | True | 576,288 rows |
| A2 complete rectangular grid | True | 138 zones x 4,176 local hour labels = 576,288 |
| A1 numeric and Boolean types | True | integer counts/calendar, float weather/rolling, Boolean flags |
| A3 finite values | True | all numeric fields finite |
| A3 count and weather ranges | True | nonnegative counts/rain/snow; probability 0--100; calendar ranges valid |
| A3 calendar derivation | True | matches pickup_hour |
| A5 weekend and holiday flags | True | 23,184 holiday rows; 7 dates; Labor Day is in warm-up |
| A6 Manhattan exact split | True | 288,144 rows; all columns and values compared |
| A6 Queens exact split | True | 288,144 rows; all columns and values compared |
| A7 trip reconciliation | True | 21,728,117 retained + 851,676 warm-up = 22,579,793 cleaned pickups |
| A7 raw collection audit | True | 23,318,979 raw pickups; 739,186 removed |
| A8 weather join integrity | True | every retained zone-hour matches source weather |
| A8 stable grid assignment | True | 50 cells for 138 zones; max 13 zones/cell |
| A8 DST audit | True | 9,166 pickups in combined 01:00 label |

**[A1/A2/A3] Schema, coverage and ranges**

- **Finding:** 576,288 rows across 138 zones, with exactly 4,176 rows per zone. All expected local hour labels are present; zero counts are observations.
- **Evidence:** [A1_schema.csv](tables/A1_schema.csv), [A3_value_ranges.csv](tables/A3_value_ranges.csv), [A2_rows_per_zone.png](figures/A2_rows_per_zone.png), [A2_zero_hour_heatmap.png](figures/A2_zero_hour_heatmap.png)
- **Implication:** Use the complete grid; dropping zeros would bias averages and temporal profiles.

**[A5/A6] Flags and borough splits**

- **Finding:** Weekend flags match Saturday/Sunday; 23,184 rows cover seven federal holiday dates. Each borough has 69 zones and 288,144 rows.
- **Evidence:** [A1_A8_data_checks.csv](tables/A1_A8_data_checks.csv)
- **Implication:** Labor Day is absent because Sep 1--7 was removed for lag warm-up; service area must not be interpreted as taxi type.

**[A7] Clean-trip reconciliation**

- **Finding:** 21,728,117 retained trips + 851,676 warm-up trips = 22,579,793 cleaned trips exactly. Warm-up demand was recovered once from lag_168h in Sep 8--14; these rows refer to Sep 1--7. Raw audit = 23,318,979; cleaning removed 739,186.
- **Evidence:** [A7_trip_reconciliation.csv](tables/A7_trip_reconciliation.csv)
- **Implication:** Use retained-period totals for EDA; a direct comparison with all six months of cleaned trips would appear to lose demand.

**[A8] DST, sparse zones and weather cells**

- **Finding:** DST 01:00 has 9,166 trips versus 6,564 on four nearby normal Sundays (1.40x, not an assumed 2x). There are 40 zones with mean <1 pickup/hour; zones 103 and 104 are entirely zero. The 138 zones use 50 weather cells, with up to 13 zones sharing a cell.
- **Evidence:** [A8_dst_comparison.png](figures/A8_dst_comparison.png), [A8_near_empty_zones.csv](tables/A8_near_empty_zones.csv), [A8_shared_weather_cells.csv](tables/A8_shared_weather_cells.csv)
- **Implication:** Do not remove sparse areas as errors. Flag DST and its lag copies; nearby Sundays differ in events/weather, and the marathon also occurs on DST day. Grid identity uses latitude/longitude; elevation metadata varies within some cells, so shared cells do not guarantee identical weather values and are not independent spatial observations.

**[B1/B2/B3/B5] Target distribution and zero prevalence**

- **Finding:** Mean=37.70, median=4, maximum=1,122; 27.7% of zone-hours are zero. Manhattan zero share=11.6%; Queens=43.7%. log1p compresses the tail while preserving zeros.
- **Evidence:** [B1_B5_target_histograms.png](figures/B1_B5_target_histograms.png), [B3_borough_service_shapes.png](figures/B3_borough_service_shapes.png), [B1_B3_ecdf.png](figures/B1_B3_ecdf.png), [B2_zero_share_by_hour.png](figures/B2_zero_share_by_hour.png), [B3_borough_distribution.csv](tables/B3_borough_distribution.csv)
- **Implication:** Compare count-based and zero-aware approaches. A log-target model needs retransformation validation; exp(prediction)-1 alone need not estimate the mean count.

**[B4] Overdispersion**

- **Finding:** 135 of 136 nonzero-demand zones have variance > mean; median variance/mean=3.53. All-zero zones have undefined variance/mean and are excluded from the log plot.
- **Evidence:** [B4_mean_variance.png](figures/B4_mean_variance.png), [B4_zone_distribution.csv](tables/B4_zone_distribution.csv)
- **Implication:** A constant-rate Poisson assumption is inadequate for pooled counts. Calendar/seasonal variation also contributes; this does not prove conditional overdispersion after modelling.

<!-- arun-issue-63:end -->

<!-- arun-issue-64:start -->

## Borough, airport and calendar patterns (#64)

Totals use all retained pickups. Group means are per zone-hour and include zeros.
Weekend ratios compare mean pickups per observed weekend/weekday hour (not totals).

**[C3] Demand by Borough**

- **Finding:** Manhattan: 19,679,535 (90.6%), mean 68.3/zone-hour across 69 zones; Queens: 2,048,582 (9.4%), mean 7.1/zone-hour across 69 zones.
- **Evidence:** [C3_group_demand.png](figures/C3_group_demand.png), [C3_group_demand.csv](tables/C3_group_demand.csv)
- **Implication:** Compare both volume and per-zone rates. Service areas are geography; this table cannot separate yellow from green taxis.

**[C4] Demand by service_zone**

- **Finding:** Airports: 1,402,967 (6.5%), mean 168.0/zone-hour across 2 zones; Boro Zone: 1,571,172 (7.2%), mean 4.6/zone-hour across 81 zones; Yellow Zone: 18,753,978 (86.3%), mean 81.7/zone-hour across 55 zones.
- **Evidence:** [C4_group_demand.png](figures/C4_group_demand.png), [C4_group_demand.csv](tables/C4_group_demand.csv)
- **Implication:** Compare both volume and per-zone rates. Service areas are geography; this table cannot separate yellow from green taxis.

**[C5] Airport timing**

- **Finding:** JFK Airport peaks at 16:00 (380.9 pickups/hour); LaGuardia Airport peaks at 14:00 (258.6 pickups/hour).
- **Evidence:** [C5_airport_profiles.png](figures/C5_airport_profiles.png), [C5_airport_hourly.csv](tables/C5_airport_hourly.csv), [C5_airport_weekly_profile.csv](tables/C5_airport_weekly_profile.csv), [C5_airport_weekly_totals.csv](tables/C5_airport_weekly_totals.csv)
- **Implication:** Plan airport pickup positioning by its own hourly and weekday pattern; flight schedules and supply are not measured here.

**[C9] Weekend-to-weekday ratios**

- **Finding:** Each zone has 3,000 weekday labels and 1,176 weekend labels. Among zones averaging >=1 pickup/hour, Maspeth has the highest ratio (4.01x); Hammels/Arverne has the lowest (0.60x). All-zero zones have an undefined ratio, not zero.
- **Evidence:** [C9_weekend_weekday_ranked.png](figures/C9_weekend_weekday_ranked.png), [C9_weekend_weekday_by_zone.csv](tables/C9_weekend_weekday_by_zone.csv)
- **Implication:** Use zone x weekend interactions; large ratios in near-empty zones may reflect tiny denominators. All flags, including holidays, are retained for this unadjusted comparison.

**[D3/D4] Calendar-adjusted totals**

- **Finding:** There are 24 complete weeks and one final six-day week. September has 23 observed days, not 30. Average daily pickups range from 111,566 (2026-01) to 134,180 (2025-09).
- **Evidence:** [D3_weekly_totals.png](figures/D3_weekly_totals.png), [D4_monthly_trips_per_day.png](figures/D4_monthly_trips_per_day.png), [D3_weekly_totals.csv](tables/D3_weekly_totals.csv), [D4_monthly_trips_per_day.csv](tables/D4_monthly_trips_per_day.csv)
- **Implication:** Compare means per observed day across months; do not interpret partial-week or partial-month totals as a full-period fall.

**[D5/D6] Hourly and weekday profiles**

- **Finding:** Peak hour=18:00 (8,996 pickups/hour); trough=04:00 (870). Busiest average day=Sat (136,529 pickups/day); quietest=Mon (105,511).
- **Evidence:** [D5_D6_calendar_profiles.png](figures/D5_D6_calendar_profiles.png), [D4_D5_D6_calendar_boxplots.png](figures/D4_D5_D6_calendar_boxplots.png), [D5_hourly_profile.csv](tables/D5_hourly_profile.csv), [D6_weekday_profile.csv](tables/D6_weekday_profile.csv)
- **Implication:** Hour and weekday have different units here. Calendar variation and zone interactions should be evaluated with time-based validation.

**[D9/D10] Time bands and changing shape**

- **Finding:** The PM 16--19 band carries 26.2%--27.4% of monthly pickups; late night 00--04 carries 7.4%--8.5%. The two monthly overlays distinguish overall volume changes from changes in time-of-day shares.
- **Evidence:** [D9_time_band_shares.png](figures/D9_time_band_shares.png), [D10_monthly_hourly_profiles.png](figures/D10_monthly_hourly_profiles.png), [D9_time_band_share.csv](tables/D9_time_band_share.csv), [D10_monthly_hourly_profiles.csv](tables/D10_monthly_hourly_profiles.csv), [D10_monthly_hourly_shares.csv](tables/D10_monthly_hourly_shares.csv)
- **Implication:** Shares measure recorded trips, not rates per band-hour; the bands have unequal durations. September's partial month and changing weekday mix can affect the overlays.

<!-- arun-issue-64:end -->

<!-- arun-issue-66:start -->

## Fleet planning and demand stability (#66)

Fleet planning charts describe pickup volume and timing. Counts alone do not estimate
vehicle availability, trip duration, airport queues or unmet demand. Historical
percentiles below are empirical pickup counts, not calibrated forecast intervals.

**[H3] Week-to-week consistency**

- **Finding:** Across 24 complete weeks, median zone correlation with the other weeks' 168-hour template is 0.90 among zones with mean >=1/hour; median CV of weekly levels=0.15. Each comparison excludes its own week from the template. Constant/all-zero profiles have undefined correlation; valid-week counts are exported.
- **Evidence:** [H3_weekly_profile_overlays.png](figures/H3_weekly_profile_overlays.png), [H3_zone_consistency.csv](tables/H3_zone_consistency.csv), [H3_weekly_profile_correlations.csv](tables/H3_weekly_profile_correlations.csv)
- **Implication:** Separate repeatable timing from changing volume. This retrospective template uses other weeks and is descriptive only; a forecasting baseline must use prior weeks.

**[H4] Hour-over-hour changes**

- **Finding:** Manhattan: mean absolute change 16.2 pickups/zone, 1st--99th percentile -100 to 84; Queens: mean absolute change 2.7 pickups/zone, 1st--99th percentile -19 to 23. 575,874 valid within-zone transitions; no cross-zone boundary differences, first-row or DST-adjacent differences.
- **Evidence:** [H4_hourly_changes.png](figures/H4_hourly_changes.png), [H4_hourly_change_summary.csv](tables/H4_hourly_change_summary.csv), [H4_change_by_hour.csv](tables/H4_change_by_hour.csv)
- **Implication:** Repositioning needs to anticipate rising slots, with larger count changes in busy Manhattan zones. Changes remain signed; zero previous counts are valid.

**[H5] Peak-to-average ratios**

- **Finding:** Among zones with mean >=1/hour, median maximum/mean=4.92; Maspeth leads at 23.79x. Ratios for all 138 zones are exported; two all-zero zones are undefined.
- **Evidence:** [H5_peak_average_ratios.png](figures/H5_peak_average_ratios.png), [H5_I3_zone_peak_demand.csv](tables/H5_I3_zone_peak_demand.csv)
- **Implication:** Maximum/mean is sensitive to one event and tiny means. Use P95/P99 and conditional calendar profiles alongside maxima.

**[I1/I2] Changing hotspots and top-N coverage**

- **Finding:** 31 distinct zones enter the top ten at some hour. Top-five coverage ranges 20.8%--37.5%; top-ten 35.5%--52.3%; top-twenty 54.9%--72.8%. Rankings use average zone pickups at each clock hour and ties use the lower zone ID.
- **Evidence:** [I1_top_zone_bump_chart.png](figures/I1_top_zone_bump_chart.png), [I1_top10_zones_each_hour.csv](tables/I1_top10_zones_each_hour.csv), [I2_topN_coverage.png](figures/I2_topN_coverage.png), [I2_topN_hourly_coverage.csv](tables/I2_topN_hourly_coverage.csv)
- **Implication:** Top-N sets change by hour and are selected retrospectively over the full period; a fixed deployment or forward test needs historical-only selection.

**[I3] Demand percentiles**

- **Finding:** Upper East Side South averages 243.2 pickups/hour, with P95=537 and P99=612. All-zero and sparse zones remain in the exported percentile table; linear empirical quantiles can be fractional.
- **Evidence:** [I3_mean_p95_p99.png](figures/I3_mean_p95_p99.png), [H5_I3_zone_peak_demand.csv](tables/H5_I3_zone_peak_demand.csv)
- **Implication:** Sizing against the average misses recurring busy hours. These unconditional pickup quantiles are not taxi counts or predictive uncertainty bounds.

**[I4] Airport demand versus Manhattan**

- **Finding:** Manhattan (all zones) peaks 18:00; JFK Airport peaks 16:00; LaGuardia Airport peaks 14:00. Manhattan represents 69 zones; each airport represents one zone. Relative profiles divide by each group's own mean.
- **Evidence:** [I4_airport_manhattan_timing.png](figures/I4_airport_manhattan_timing.png), [I4_airport_manhattan_hourly.csv](tables/I4_airport_manhattan_hourly.csv)
- **Implication:** Compare timing on a normalised scale; the borough's much larger level would otherwise hide the airport shapes.

**[I5] Night hotspots**

- **Finding:** 00--04 leader: East Village (183.5 pickups/hour). Friday/Saturday 20:00--04:59 leader: East Village (455.5/hour). Weekend nights are assigned to their evening date: early Sat/Sun is included; early Fri is not. Means use actual available hour labels (boundary nights may be partial).
- **Evidence:** [I5_night_hotspots.png](figures/I5_night_hotspots.png), [I5_night_hotspot_map.png](figures/I5_night_hotspot_map.png), [I5_night_hotspots.csv](tables/I5_night_hotspots.csv)
- **Implication:** Nightlife positioning differs from commuter coverage. Centroids are location proxies and do not identify exact pickup points or driving routes.

**[I6] Boro Zone demand**

- **Finding:** The Boro Zone service area contains 81 zones. Manhattan peaks at 17:00 (26.01 pickups/zone-hour); Queens peaks at 07:00 (3.33 pickups/zone-hour).
- **Evidence:** [I6_boro_zone_hourly.png](figures/I6_boro_zone_hourly.png), [I6_boro_zone_hourly.csv](tables/I6_boro_zone_hourly.csv)
- **Implication:** Normalise by zone count and keep sparse areas visible. Boro Zone counts include both yellow and green taxis; supply requirements cannot be inferred from pickups alone.

<!-- arun-issue-66:end -->

<!-- arun-issue-65:start -->

## Holidays, special days and modelling suggestions (#65)

Normal-day baseline: up to six nearest dates of the **same weekday within +/-28 days**,
with ties favouring the earlier date; at least three are required. Controls exclude
the seven recurring federal holidays, Halloween and its next morning, the marathon/DST
day, Thanksgiving week (Nov 24--30), the Christmas/New Year period (Dec 20--Jan 4),
and heavy-snow days (median across zone daily snowfall totals >=5 cm). The exact control
dates, counts, range and standard deviation are exported. A +/-42-day sensitivity uses
the same exclusion rules and cap of six. IQR shading shows control-day variability,
not a confidence interval. These local comparisons remain affected by weather, trend,
events and supply; they are descriptive changes rather than causal holiday effects.
The calendar is the upstream recurring federal calendar, with special days analysed
separately. [Federal holiday dates](https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/).
The marathon date is grounded in [NYRR's 2025 results](https://results.nyrr.org/event/M2025/result/9).

| date | event | actual_trips | normal_mean_trips | pct_change | control_days |
|---|---|---|---|---|---|
| 2025-10-13 | Columbus Day | 104735 | 114190 | -8.3% | 6 |
| 2025-11-11 | Veterans Day | 123875 | 130882 | -5.4% | 6 |
| 2025-11-27 | Thanksgiving Day | 86029 | 155811 | -44.8% | 6 |
| 2025-12-25 | Christmas Day | 60817 | 143269 | -57.6% | 6 |
| 2026-01-01 | New Year's Day | 102562 | 143269 | -28.4% | 6 |
| 2026-01-19 | Martin Luther King Jr. Day | 93566 | 93566 | +0.0% | 5 |
| 2026-02-16 | Washington's Birthday | 81311 | 90738 | -10.4% | 3 |

**[E1] Seven federal holidays**

- **Finding:** Largest decline: Christmas Day, -57.6% relative to its matched normal weekday. All seven holidays have citywide and borough results (21 rows) in holiday_effects.csv. Labor Day cannot be estimated from features.csv because it is in the removed warm-up week. Control counts range 3--6.
- **Evidence:** [E1_holiday_pct_change.png](figures/E1_holiday_pct_change.png), [E1_holiday_hourly_profiles.png](figures/E1_holiday_hourly_profiles.png), [holiday_effects.csv](tables/holiday_effects.csv), [E1_holiday_hourly_profiles.csv](tables/E1_holiday_hourly_profiles.csv), [E1_control_exclusions.csv](tables/E1_control_exclusions.csv)
- **Implication:** Use holiday identity and interactions, not only one pooled is_holiday coefficient. There is one observation of each holiday, so validate any proposed effect out of time.

Baseline sensitivity matters: MLK Day changes from +0.0% with +/-28-day controls to -7.8% with +/-42-day controls. Where the same nearest six dates are selected, the sensitivity result is identical by construction. Late-period holidays have fewer eligible controls because the dataset ends on Feb 28.

**[E2] Holiday periods**

- **Finding:** Thanksgiving week: -24.4% across the period; Christmas / New Year: -26.8% across the period. Each day's reference matches its own weekday, rather than comparing the entire period with a single day.
- **Evidence:** [E2_holiday_periods.png](figures/E2_holiday_periods.png), [E2_holiday_periods.csv](tables/E2_holiday_periods.csv)
- **Implication:** Holiday-period flags and lead/lag days may capture effects missed by exact holiday dates; local seasonal changes still confound the comparisons.

**[E3] New Year's Eve night**

- **Finding:** The episode is Dec 31 20:00--Jan 1 04:59 (nine hour labels). Total pickups=58,216 versus 35,937 on 6 normal Wednesday nights (+62.0%). All 138 zones and 1,242 zone-hour comparisons are exported; the chart shows the eight largest episode totals.
- **Evidence:** [E3_new_year_night_profiles.png](figures/E3_new_year_night_profiles.png), [E3_new_year_night_by_zone.csv](tables/E3_new_year_night_by_zone.csv), [E3_new_year_night_hourly.csv](tables/E3_new_year_night_hourly.csv)
- **Implication:** A calendar-day holiday flag splits this cross-midnight event. Use a night-event flag attached to the full episode; top zones here are retrospective selections.

**[E4] Special days**

- **Finding:** Halloween: +9.1%; NYC Marathon: +13.7%; Black Friday: -38.8%; Christmas Eve: -30.9%. The marathon coincides with DST; omitting 01:00 from both event and controls gives +12.0% versus +13.7% with all labels. Halloween's calendar-day profile excludes the following night's spillover; the model recommendation covers both dates.
- **Evidence:** [E4_special_day_profiles.png](figures/E4_special_day_profiles.png), [E4_special_day_effects.csv](tables/E4_special_day_effects.csv), [E4_marathon_DST_sensitivity.csv](tables/E4_marathon_DST_sensitivity.csv)
- **Implication:** Event flags may help, but marathon and DST effects cannot be separated causally from this one day. Black Friday and Christmas Eve are analysed separately from recurring federal flags.

**[D8] Weekday, weekend and holiday shapes**

- **Finding:** Holiday: 7 days, peak 18:00; Weekday (nonholiday): 118 days, peak 18:00; Weekend (nonholiday): 49 days, peak 18:00. Holiday takes priority so classes are disjoint. Weekday/weekend profiles retain special non-federal days and are pooled over months.
- **Evidence:** [D8_day_class_profiles.png](figures/D8_day_class_profiles.png), [D8_day_class_hourly.csv](tables/D8_day_class_hourly.csv)
- **Implication:** Volume and shape both differ. Seven holidays are heterogeneous; this pooled comparison should not replace holiday-specific profiles.

**[G9] Modelling features suggested by all four analyses**

- **Finding:** Nine candidate feature families are exported after #63, #64 and #66. They target geographic/calendar interactions, cross-midnight events, holiday periods, DST and seasonal level shifts. These are proposals; no feature engineering, model fitting or association-rule mining is included in this Review 1 work.
- **Evidence:** [G9_suggested_features.csv](tables/G9_suggested_features.csv)
- **Implication:** Retain existing lags and weather features for later ablation. Select candidate features using chronological validation; zone-level summaries must be learned on training data only.

| candidate_feature | evidence_ids | validation_note |
|---|---|---|
| zone_x_hour_x_weekday | G9; D5/D6; C5; I4 | Learn coefficients/encodings on training history only |
| zone_x_weekend_night | G9; C9; I5 | Assign 00--04 to the preceding evening date |
| holiday_name_x_hour | G9; E1; D8 | One observed example per holiday; test out of time |
| holiday_period_and_distance | G9; E2 | Fix event definitions before evaluation; avoid target-derived cutoffs |
| special_night_event | G9; E3/E4 | Match cross-midnight windows; no post-event counts as inputs |
| DST_and_affected_lags | G9; A8 | Naive labels cannot recover the two physical hours; holiday flags cannot flag DST |
| seasonal_time_features | G9; D3/D4; D10; H3 | Only six months: annual seasonality not established |
| zone_demand_level_and_sparsity | G9; B2/B4; H5 | Compute on training history or lagged rolling history, never full-data summaries |
| zone_weather_cell_metadata | G9; A8 | Elevation may vary within cell; this is an evaluation/grouping candidate, not proven predictive gain |

<!-- arun-issue-65:end -->
