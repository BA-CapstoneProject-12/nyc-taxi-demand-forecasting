"""Tests for category semantics and separation of training/test information."""
import copy
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import association_rule_data_preparation as arm


def toy_history():
    """Three different weekly shapes with a future holdout and one sparse zone."""
    hours = pd.date_range("2025-09-08", periods=21*24, freq="h")
    records = []
    for zone in [1, 2, 3, 4]:
        for time in hours:
            h, day = time.hour, time.dayofweek
            counts = {1: 2+30*int(7 <= h <= 9), 2: 3+25*int(12 <= h <= 18),
                      3: 2+40*int(day >= 5 and h <= 4), 4: 0}
            records.append({"PULocationID": zone, "pickup_hour": time, "trip_count": counts[zone],
                "hour": h, "day_of_week": day, "month": time.month, "is_weekend": day >= 5,
                "is_holiday": False, "apparent_temperature": float(h), "rain": .1 if h == 8 else 0.,
                "snowfall": .2 if h == 8 else 0., "precipitation_probability": 0,
                "split": "train" if time < pd.Timestamp("2025-09-22") else "test",
                "is_dst_merged_hour": False, "Borough": "Test", "Zone": str(zone), "service_zone": "Test"})
    return pd.DataFrame(records)


class AssociationPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = toy_history()
        cls.params, _ = arm.fit_parameters(cls.frame)

    def test_holdout_values_cannot_change_any_fitted_parameter(self):
        changed = self.frame.copy()
        future = changed["split"].eq("test")
        changed.loc[future, "trip_count"] = 100000
        changed.loc[future, "apparent_temperature"] = -1000.
        changed.loc[future, "rain"] = 100.
        params, _ = arm.fit_parameters(changed)
        self.assertEqual(params, self.params)

    def test_temperature_boundaries_and_unseen_extremes(self):
        values = [-100., *self.params["temperature_cuts_c"], 100.]
        frame = self.frame.iloc[:4].copy()
        frame["apparent_temperature"] = values
        rows = arm.transform(frame, self.params)
        self.assertEqual(rows.temperature.tolist(), ["lower", "lower", "middle", "upper"])

    def test_tied_counts_are_never_artificially_split(self):
        params = copy.deepcopy(self.params)
        for zone in params["zones"]:
            if zone["PULocationID"] == 1:
                zone["q_low"] = 2.
                zone["q_high"] = 2.
        frame = self.frame.iloc[:4].copy()
        frame["trip_count"] = [0, 2, 2, 3]
        self.assertEqual(arm.transform(frame, params).demand.tolist(), ["Low", "Low", "Low", "High"])

    def test_zero_rows_remain_and_sparse_zones_are_audited(self):
        frame = self.frame.copy()
        frame.loc[0, "trip_count"] = 0
        rows = arm.transform(frame, self.params)
        self.assertEqual(len(rows), len(frame))
        self.assertTrue(rows.iloc[0].mining_eligible)
        self.assertEqual(rows.iloc[0].demand, "Low")
        sparse_zone = rows.loc[rows.PULocationID.eq(4)]
        self.assertFalse(sparse_zone.mining_eligible.any())
        self.assertTrue(sparse_zone.demand.eq("Low").all())

    def test_dst_is_excluded_from_both_fit_and_mining(self):
        frame = self.frame.copy()
        frame.loc[0, "is_dst_merged_hour"] = True
        a, _ = arm.fit_parameters(frame)
        frame.loc[0, "trip_count"] = 100000
        frame.loc[0, "apparent_temperature"] = -1000.
        b, _ = arm.fit_parameters(frame)
        self.assertEqual(a, b)
        self.assertFalse(arm.transform(frame, a).iloc[0].mining_eligible)

    def test_rain_and_snow_can_both_be_present(self):
        frame = self.frame.iloc[:2].copy()
        frame["rain"] = [0., .1]
        frame["snowfall"] = [0., .2]
        rows = arm.transform(frame, self.params)
        self.assertEqual(rows.rain.tolist(), ["no", "yes"])
        self.assertEqual(rows.snow.tolist(), ["no", "yes"])

    def test_time_band_and_weekend_boundaries(self):
        frame = self.frame.iloc[:8].copy()
        frame["hour"] = [4, 5, 6, 7, 9, 10, 19, 20]
        frame["is_weekend"] = [False, True]*4
        rows = arm.transform(frame, self.params)
        self.assertEqual(rows.time_band.tolist(), ["late_night", "early_morning", "early_morning", "am_rush", "am_rush", "midday", "pm_rush", "evening"])
        self.assertEqual(rows.day_type.tolist(), ["weekday", "weekend"]*4)

    def test_unknown_zone_and_category_fail_clearly(self):
        frame = self.frame.iloc[:1].copy()
        frame["PULocationID"] = 999
        with self.assertRaisesRegex(ValueError, "New zone"):
            arm.transform(frame, self.params)
        rows = arm.transform(self.frame.iloc[:1], self.params)
        rows["temperature"] = "unknown"
        with self.assertRaisesRegex(ValueError, "Unknown temperature"):
            arm.encode(rows)

    def test_fixed_boolean_vocabulary_and_exact_decoding(self):
        rows = arm.transform(self.frame.iloc[:50], self.params)
        catalog = arm.item_catalog()
        matrix = arm.encode(rows, catalog)
        self.assertEqual(matrix.dtype, bool)
        self.assertEqual(matrix.shape, (50, 24))
        self.assertTrue(np.all(np.asarray(matrix.sum(axis=1)).ravel() == 8))
        for i in [0, 8, 49]:
            decoded = set(catalog.iloc[matrix[i].indices]["item"])
            expected = {f"{family}={rows.iloc[i][family]}" for family in arm.FAMILIES}
            self.assertEqual(decoded, expected)
        self.assertTrue(catalog.loc[catalog.family.eq("demand"), "role"].eq("consequent_only").all())


if __name__ == "__main__":
    unittest.main()
