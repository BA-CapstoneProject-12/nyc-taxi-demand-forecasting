# nyc-taxi-demand-forecasting
NYC taxi demand forecasting using historical Yellow Taxi trips and weather data, with machine learning, time-series forecasting, association rule mining, feature engineering, and an interactive dashboard for demand insights and fleet planning.

## Data collection

Scope: **Manhattan + Queens** (138 taxi zones), **yellow + green taxis**, **Sep 2025 – Feb 2026**, with hourly weather for each taxi zone.

| Source | Used for |
|---|---|
| [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) | Trip pickup/dropoff times and zones, taxi zone lookup and boundaries |
| [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) | Hourly apparent temperature, rain, snowfall, precipitation probability per zone |

Full dataset: `data/raw/NYC-taxi-demand-Manhattan-Queens.csv`, with **23,318,979 trips**. Each trip has its pickup/dropoff time, pickup/dropoff zone and the weather at its pickup zone and hour. The file is 3.2 GB, too large for GitHub, so it is shared as a private Kaggle dataset. The notebook below can also rebuild it. The zone list, hourly weather per zone and collection summary are small and are in `data/raw/` in this repo.

- [data/DATA_GUIDE.md](data/DATA_GUIDE.md): what each data file is, and how to get and use the dataset
- [docs/data_collection.md](docs/data_collection.md): sources, collection steps, output files, dataset summary and known issues
- [docs/data_dictionary.md](docs/data_dictionary.md): every field, its purpose, and why these fields were chosen

### Reproduce

All the collection code is in [`scripts/data_collection.ipynb`](scripts/data_collection.ipynb), with an explanation of each step. Install the packages, then run all cells. The first run downloads ~425 MB of TLC files and takes about 15 minutes.

```bash
pip install -r requirements.txt
```


## Project structure

```
data/
  DATA_GUIDE.md   what each file is and how to get and use the dataset
  raw/            everything collected: full dataset (on Kaggle), zones, weather, summary
  processed/      empty, for the next stages of the project
docs/
  data_collection.md
  data_dictionary.md
scripts/
  data_collection.ipynb   all data collection code: zones, weather API, TLC trips,
                          weather join and dataset profile
```
