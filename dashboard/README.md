# Interactive dashboard

A Streamlit app that tells the story of the project, chapter by chapter, and
lets users try the models live.

| Section | Page | What it shows |
|---|---|---|
| Overview | Home | Business problem, deliverables, story map, team |
| The story | 1 · Data collection & cleaning | Sources, zone map, trip funnel, cleaning rules, features |
| | 2 · Exploring demand | Where / when / weather / holidays, plus a zone explorer |
| | 3 · Predicting demand | Linear Regression, Random Forest, HistGradientBoosting vs baseline |
| | 4 · Forecasting ahead | Time-series Model 1, results, teammate models (DHR, MSTL + ETS) |
| | 5 · Demand rules | Apriori vs FP-Growth, holdout validation, rule explorer |
| | 6 · Business impact | Recommendations, conclusion, limitations, future scope |
| Try it live | Demand predictor | Runs the saved HistGradientBoosting model on any zone, hour and what-if weather |
| | Forecast planner | Runs time-series Model 1 for a day or week ahead (any area or zone) |
| | Dispatch advisor | Matches a situation against the 152 validated association rules |

## Run it

You need Python 3.10 or newer. Every command below starts in the repository
root (the `nyc-taxi-demand-forecasting` folder). The virtual environment is
created as `.venv` in that folder; it is already listed in `.gitignore`.

### macOS

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install the dashboard packages
pip install --upgrade pip
pip install -r dashboard/requirements.txt

# 3. Build the dashboard data (one time only; skip if dashboard/data/ already has files)
python dashboard/build_data.py

# 4. Start the dashboard
streamlit run dashboard/app.py
```

Next time, only activate the environment and start the app:

```bash
source .venv/bin/activate
streamlit run dashboard/app.py
```

### Windows (PowerShell)

```powershell
# 1. Create and activate a virtual environment
py -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install the dashboard packages
python -m pip install --upgrade pip
pip install -r dashboard\requirements.txt

# 3. Build the dashboard data (one time only; skip if dashboard\data\ already has files)
python dashboard\build_data.py

# 4. Start the dashboard
streamlit run dashboard/app.py
```

Next time, only activate the environment and start the app:

```powershell
.venv\Scripts\Activate.ps1
streamlit run dashboard/app.py
```

If PowerShell refuses to run `Activate.ps1` ("running scripts is disabled"),
allow it for your user once and try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

In Command Prompt (cmd) instead of PowerShell, activate with
`.venv\Scripts\activate.bat`.

### Notes

- The app opens at http://localhost:8501. Stop it with `Ctrl + C` in the terminal.
- Always run `streamlit` from the repository root so the theme in
  `.streamlit/config.toml` (at the repository root) is applied. Streamlit
  Community Cloud runs the app the same way.
- When you are done, leave the virtual environment with `deactivate`.
- The app's font (Inter) loads from Google Fonts. Without internet the app uses
  the system font instead; everything else works the same.
- The app works fully offline. Only step 3 needs internet the first time: it
  downloads the official taxi-zone outlines from NYC Open Data and saves them as
  `data/taxi_zones.geojson`.
- Step 3 reads `data/processed/features.csv` and the model outputs in `models/`.
  If those files are missing, run the project notebooks first (see the main README).

## Deploy on Streamlit Community Cloud (free)

1. Sign in at [share.streamlit.io](https://share.streamlit.io) with GitHub.
2. Click **Create app** and choose the repository, branch `main` and main file
   path `dashboard/app.py`.
3. Under **Advanced settings**, choose Python 3.12.
4. Click **Deploy**. Community Cloud installs `dashboard/requirements.txt` and
   reads the theme from `.streamlit/config.toml` at the repository root. All data
   files are already in the repository, so no build step is needed.

The first visit after the app wakes up takes a little longer while the data loads.

## Files

```text
dashboard/
  app.py            entry point: page setup and sidebar navigation
  utils.py          paths, colours, layout helpers, data loaders, model helpers
  build_data.py     joins saved project outputs into small files in data/
  views/            one file per page (home, ch1-ch6, three live tools)
  data/             files written by build_data.py
  assets/           extra images shown in the app (teammate Model 2 charts)
```

The theme lives in `.streamlit/config.toml` at the repository root.

## Where the numbers come from

Nothing is re-trained by the dashboard. It reads the outputs already saved in the
repository:

- `data/processed/features.csv`: modelling table used by the Demand predictor
- `models/modeling/model_3_hist_gradient_boosting.joblib` plus prediction and metric CSVs (Review 1)
- `data/processed/time_series/` and `models/time_series/model_1/tables/` (Review 2 time series)
- `models/time_series/model_1/tsa/baselines.py`: the Forecast planner imports the
  team's forecasting functions directly, so live forecasts match the saved results
- `data/processed/arm_findings/` and `data/processed/association_rules/` (Review 2 rules)
- `EDA_doc/tables/` and `EDA_doc/figures/` (EDA)
