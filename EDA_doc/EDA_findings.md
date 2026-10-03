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
