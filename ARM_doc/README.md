# Association Rule Data Preparation

Arun N's Review 2 contribution for [issue #30](https://github.com/BA-CapstoneProject-12/nyc-taxi-demand-forecasting/issues/30).

This prepares the categorical inputs for the member handling association rule mining.
Each transaction is one zone during one recorded hour, with time band, weekday/weekend,
holiday flag, rain/snow flags, temperature band, zone cluster and a relative demand class.

- [Preparation method, boundaries, output schemas and handoff](../data/dataset-documents/association_rule_preparation.md)
- [Executed notebook](../scripts/association_rule_data_preparation.ipynb)
- [Reusable preparation/loader script](../scripts/association_rule_data_preparation.py)
- [Prepared files](../data/processed/association_rules/)
- [Item support chart](figures/arm_item_support.png)
- [Demand-class balance chart](figures/arm_demand_class_balance.png)
- [Zone demand threshold chart](figures/arm_zone_thresholds.png)

```bash
python scripts/association_rule_data_preparation.py
python scripts/association_rule_data_preparation.py --validate-only
python -m unittest discover -s tests -v
```

The default mining population has 96 training-selected active zones, 320,544 training
transactions and 80,256 held-out test transactions. The audit retains all 576,288
source rows. Every zero in an eligible zone remains. The merged DST hour and 42 sparse
zones have explicit exclusion reasons.

All data-derived bins and cluster assignments are fitted on training only. Train and
test use the same 24-item Boolean vocabulary. Use the `load_transactions()` helper
to obtain aligned sparse Boolean pandas data and metadata. The `demand=` items belong
only in the consequent of downstream rules. Mining, rule interpretation and test-period
stability are the subsequent members' tasks (#31--#33).
