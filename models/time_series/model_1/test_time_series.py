"""Behavioral tests for information boundaries and forecasting edge cases."""
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
import pandas as pd
from tsa.baselines import seasonal_naive,seasonal_mean,adaptive_week,tsb
from tsa.models import hourly_forecast,daily_forecast
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

    def test_forecasts_ignore_future_targets_weather_and_fourier_columns(self):
        index=pd.date_range("2025-09-01",periods=1056,freq="h")
        calendar=pd.DataFrame(index=index)
        history=20+10*np.sin(np.arange(1008)*2*np.pi/24)
        future=calendar.iloc[1008:].copy()
        for name in ("naive_24","naive_168","mean_4weeks","adaptive_week"):
            original=hourly_forecast(name,history,calendar.iloc[:1008],future)
            poisoned=future.assign(trip_count_adj=1e9,snowfall=1e6,fourier_daily_sin_1=-999)
            changed=hourly_forecast(name,history,calendar.iloc[:1008],poisoned)
            np.testing.assert_array_equal(original,changed)

    def test_model_registry_excludes_teammate_forecasters(self):
        from tsa.config import HOURLY_MODELS,DAILY_MODELS
        forbidden={"harmonic_ar","harmonic_ar_calendar","mstl_ets","ets_weekly","sarima_weekly"}
        self.assertFalse(forbidden.intersection(HOURLY_MODELS+DAILY_MODELS))
        for name in forbidden:
            with self.assertRaises(ValueError):
                hourly_forecast(name,np.ones(1008),pd.DataFrame(),pd.DataFrame(index=range(24)))

    def test_daily_adaptation_preserves_constant_and_zero_series(self):
        for value in (0.,15.):
            for name in ("naive_7","mean_4weeks_daily","adaptive_week_daily"):
                np.testing.assert_allclose(daily_forecast(name,np.full(100,value),7),value)

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
