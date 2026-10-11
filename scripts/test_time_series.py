"""Behavioral tests for information boundaries and forecasting edge cases."""
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
import pandas as pd
from tsa.baselines import seasonal_naive,seasonal_mean,adaptive_week,tsb
from tsa.harmonic import design,harmonic_forecast
from tsa.metrics import scores,interval_scores
from tsa.intervals import corrected_quantile,lead_bucket
from tsa.backtest import select_models
from tsa.config import SERIES,EVENT_FEATURES

class ForecastTests(unittest.TestCase):
    def test_naive_multiweek_repeats_only_last_observed_week(self):
        y=np.arange(1008)
        pred=seasonal_naive(y,400,168)
        np.testing.assert_array_equal(pred,np.tile(y[-168:],3)[:400])

    def test_panel_seasonal_mean_respects_zone_axis(self):
        y=np.column_stack([np.arange(1008),2*np.arange(1008)])
        pred=seasonal_mean(y,168)
        np.testing.assert_allclose(pred[:,1],2*pred[:,0])
        np.testing.assert_allclose(pred[:,0],y[-672:,0].reshape(4,168).mean(axis=0))

    def test_zero_history_is_safe_for_all_baselines(self):
        y=np.zeros((1008,3))
        for method in (seasonal_mean,adaptive_week,tsb):
            np.testing.assert_array_equal(method(y,168),np.zeros((168,3)))

    def test_intermittent_probability_decays_during_no_demand(self):
        y=np.r_[np.ones(100)*4,np.zeros(100)]
        self.assertLess(tsb(y,1)[0,0],tsb(y[:100],1)[0,0]/100)

    def test_future_target_and_weather_cannot_enter_harmonic_design(self):
        index=pd.date_range("2025-09-01",periods=400,freq="h")
        calendar=pd.DataFrame({name:0 for name in EVENT_FEATURES},index=index)
        calendar["trip_count"]=np.arange(400)
        calendar["rain"]=0
        original=design(calendar)
        calendar["trip_count"]=-999;calendar["rain"]=1000
        pd.testing.assert_frame_equal(original,design(calendar))
        self.assertEqual(np.linalg.matrix_rank(np.c_[np.ones(400),original.iloc[:,:40]]),41)

    def test_harmonic_forecast_is_invariant_to_future_truth(self):
        index=pd.date_range("2025-09-01",periods=1056,freq="h")
        calendar=pd.DataFrame({name:0 for name in EVENT_FEATURES},index=index)
        history=20+10*np.sin(np.arange(1008)*2*np.pi/24)+np.arange(1008)*.001
        future=calendar.iloc[1008:].copy()
        a=harmonic_forecast(history,calendar.iloc[:1008],future)
        future["trip_count_adj"]=1e9;future["snowfall"]=1e6
        b=harmonic_forecast(history,calendar.iloc[:1008],future)
        np.testing.assert_allclose(a,b)
        self.assertTrue(np.isfinite(a).all() and (a>=0).all())

    def test_metrics_do_not_invent_zero_demand_percentages(self):
        result=scores(np.zeros(10),np.zeros(10),np.zeros(200))
        self.assertEqual(result["MAE"],0)
        self.assertTrue(np.isnan(result["WAPE"]) and np.isnan(result["MASE"]) and np.isnan(result["R2"]))

    def test_metrics_reject_misaligned_arrays(self):
        with self.assertRaises(ValueError): scores([1,2],[1])
        with self.assertRaises(ValueError): scores([1,np.nan],[1,2])

    def test_finite_sample_quantile_and_horizon_bins(self):
        self.assertEqual(corrected_quantile(np.arange(1,11),.8),9)
        self.assertEqual(corrected_quantile(np.arange(1,11),.95),10)
        self.assertEqual(list(lead_bucket([1,24,25,72,73,168],168)),
                         ["001-024","001-024","025-072","025-072","073-168","073-168"])

    def test_interval_score_penalizes_misses(self):
        good=interval_scores([5],[4],[6],.2)
        bad=interval_scores([10],[4],[6],.2)
        self.assertGreater(bad["interval_score"],good["interval_score"])

    def test_calibration_folds_cannot_change_model_selection(self):
        rows=[]
        for sid in SERIES:
            for fold in range(1,7):
                for name in ("a","b"):
                    error=(1 if name=="a" else 2) if fold<=4 else (1000 if name=="a" else 0)
                    rows.extend(dict(series_id=sid,model=name,fold=fold,actual=0,prediction=error) for _ in range(168))
        with TemporaryDirectory() as directory,patch("tsa.backtest.TABLES",Path(directory)):
            selected=select_models(pd.DataFrame(rows),("a","b"),"hourly")
        self.assertTrue(all(name=="a" for name in selected.values()))

if __name__=="__main__": unittest.main(verbosity=2)

