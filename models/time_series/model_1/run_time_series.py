"""Run from any directory: python models/time_series/model_1/run_time_series.py --stage all."""
import argparse
import os
# Small matrix fits are faster and reproducible with bounded BLAS parallelism.
for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ.setdefault(name,"1")
from threadpoolctl import threadpool_limits
from tsa.config import ensure_output
from tsa.data import audit,load_inputs

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",choices=["all","audit","diagnostics","hourly","daily","zones","report"],default="all")
    args=parser.parse_args()
    ensure_output()
    with threadpool_limits(limits=1):
        data=audit() if args.stage in ("all","audit") else load_inputs()
        calendar,hourly,daily,zones,profile,folds=data
        if args.stage in ("all","diagnostics"):
            from tsa.diagnostics import diagnose
            diagnose(hourly)
        if args.stage in ("all","hourly"):
            from tsa.backtest import run_hourly
            from tsa.intervals import calibrate,block_bootstrap_comparison
            selected,predictions=run_hourly(calendar,hourly,folds)
            calibrate(predictions,selected)
            block_bootstrap_comparison(predictions,selected)
        if args.stage in ("all","daily"):
            from tsa.backtest import run_daily
            run_daily(daily,folds)
        if args.stage in ("all","zones"):
            from tsa.zones import run_zones
            run_zones(calendar,zones,profile,folds)
        if args.stage in ("all","report"):
            from tsa.reporting import report
            report(calendar,hourly,daily,profile)
    print("Finished stage: "+args.stage,flush=True)

if __name__=="__main__":
    main()
