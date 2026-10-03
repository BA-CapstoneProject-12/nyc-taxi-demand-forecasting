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
