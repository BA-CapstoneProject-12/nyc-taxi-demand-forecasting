# Arun's Review 1 EDA

Owner: [ArunN2005](https://github.com/ArunN2005). Scope: issues
[#63](https://github.com/BA-CapstoneProject-12/nyc-taxi-demand-forecasting/issues/63),
[#64](https://github.com/BA-CapstoneProject-12/nyc-taxi-demand-forecasting/issues/64),
[#65](https://github.com/BA-CapstoneProject-12/nyc-taxi-demand-forecasting/issues/65),
[#66](https://github.com/BA-CapstoneProject-12/nyc-taxi-demand-forecasting/issues/66).

Start with [EDA_findings.md](EDA_findings.md). Each finding gives measured results,
linked evidence and an implication. Charts are in [figures/](figures/) and the exact
supporting statistics are in [tables/](tables/).

## Reproduce

From the repository root, with the dependencies in `requirements.txt` installed:

```bash
python scripts/eda_arun.py
python scripts/validate_eda_arun.py
```

Alternatively open [scripts/EDA_Arun.ipynb](../scripts/EDA_Arun.ipynb) and run all cells.
The executed notebook displays representative results and links to all saved artifacts;
the calculations live in [scripts/eda_arun.py](../scripts/eda_arun.py).
The analysis runs locally with the feature files already in the repository; no raw
trip download, network connection, or private Kaggle access is required.

Optional single-issue reruns:

```bash
python scripts/eda_arun.py --issues 63
python scripts/eda_arun.py --issues 64
python scripts/eda_arun.py --issues 66
python scripts/eda_arun.py --issues 65
```

The full run follows **63, 64, 66, 65**: checks first and G9 last, as the issues request.
Issue 65 requires the earlier checks/calendar/fleet tables. Inputs are read only.
Outputs are overwritten in `EDA_doc/`; generated findings replace only their own
marked sections, preserving unrelated sections. Violin plots use a seeded sample
of up to 8,000 observations per group; other statistics use all eligible rows.

## Coverage

| Issue | Assigned analysis IDs | Main deliverables |
|---|---|---|
| #63 | A1, A2, A3, A5, A6, A7, A8; B1, B2, B3, B4, B5 | Validation audit, trip reconciliation, DST/weather/sparse-zone notes, target distributions |
| #64 | C3, C4, C5, C9; D3, D4, D5, D6, D9, D10 | Borough/service-area comparisons, airport profiles, exposure-adjusted ratios, calendar profiles |
| #66 | H3, H4, H5; I1, I2, I3, I4, I5, I6 | Weekly consistency, changes/peaks, hourly top ten, coverage, empirical percentiles, night maps, outer-area profiles |
| #65 | E1, E2, E3, E4; D8, G9 | Holiday and event comparisons, cross-midnight New Year profiles, `holiday_effects.csv`, candidate modelling features |

Combined chart filenames contain all applicable IDs. Some IDs are checks or tables
rather than separate figures. [artifact_catalog.csv](tables/artifact_catalog.csv)
lists the generated figure/table paths. [input_manifest.csv](tables/input_manifest.csv)
records SHA-256 fingerprints of the seven inputs; the validator checks that they still
match. [execution_environment.csv](tables/execution_environment.csv) records package
versions. The source and notebook are part of this branch's four issue commits.

## Interpretation and denominators

- **Coverage:** 138 zones x 4,176 hour labels = 576,288 rows, Sep 8 2025--Feb 28 2026.
  Each borough has 69 zones. Zero-demand rows remain in every applicable statistic.
- **Warm-up:** Sep 1--7 is absent from the feature rows. The 168-hour lags in Sep 8--14
  recover those pickups once for reconciliation only; those lags are not added to EDA
  totals. September monthly means divide by 23 observed days. The final week has six
  days and is marked partial; weekly consistency uses only the 24 full weeks.
- **Local clock:** timestamps are naive New York time. Nov 2 2025 01:00 combines two
  physical hours. Rates otherwise use recorded labels; H4 drops both transitions
  adjacent to this combined label. The marathon analysis also omits 01:00 from the
  event and controls as a sensitivity check, without changing source data.
- **Geography:** `service_zone` is an area category, not taxi type. Counts pool yellow
  and green taxis. Horizontal weather cells use grid latitude/longitude; elevation
  metadata can differ within a shared cell. Map dots are zone centroids, not pickups.
- **Holiday controls:** up to six nearest normal dates of the same weekday within
  +/-28 days, excluding holidays, special dates, holiday periods and heavy snow
  (median zone-day snowfall >=5 cm). A minimum of three is required. Exact dates and
  +/-42-day sensitivity are exported. These retrospective controls can use later
  dates; they must not be used as forecast features. Comparisons are descriptive.
- **Night windows:** late night is 00:00--04:59. Weekend nights are Fri/Sat
  20:00--04:59 the following day; early Sat/Sun belongs to the preceding evening.
  New Year's Eve covers Dec 31 20:00--Jan 1 04:59 and uses normal Wednesday nights.
- **Fleet quantities:** top-N coverage selects the busiest zones separately at each
  clock hour. P95/P99 are historical unconditional pickup quantiles. They do not
  estimate the number of available taxis, unmet demand, or forecast intervals.
- **Model proposals:** G9 records candidates for future validation. Zone summaries,
  percentile thresholds and hotspot selection must be computed on training history
  in forward evaluations. No models or Review 2 association rules are implemented.

Dates were verified against the [OPM recurring federal holiday schedule](https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/)
and [NYRR's 2025 marathon results](https://results.nyrr.org/event/M2025/result/9).
