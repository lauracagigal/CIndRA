---
name: regional-temperature
description: Compute per-station regional air-temperature indicators (mean/min/max annual temperature, diurnal range, hot days, cold nights) across every station in a region, build Pacific EEZ trend maps and a regional-mean anomaly time series, with an optional ERA5 background for mean annual temperature. Use when working on notebooks/historical/Regional/air_temperature/regional_indicators.ipynb or answering questions about Pacific-wide/regional temperature maps or trends.
---

## Skill: Regional Air-Temperature Indicators (notebook `notebooks/historical/Regional/air_temperature/regional_indicators.ipynb`)

### Purpose
For every station saved by `Regional/00_regional_setup.ipynb`, compute the **same air-temperature indicators used at the single-site level** (`notebooks/historical/National/air_temperature/`) and collect them into one regional dataset that can be mapped across the Pacific EEZ area. Mirrors `Regional/rainfall/regional_indicators.ipynb` cell-for-cell. The per-station formulas live in `functions/rainfall_regional.py` (`_station_temperature_indicators` / `compute_regional_temperature_indicators`) — this notebook stays thin: load → compute → save → map.

### Indicator mapping to the National notebooks
- `a_mean_temperature.ipynb` → `tmean_annual` (annual mean of `TMEAN = (TMAX + TMIN) / 2`).
- `b_min_max_temperature.ipynb` → `tmin_annual`, `tmax_annual`, `diff_annual` (diurnal range).
- `c_hot_cold_days.ipynb` → `hot_days_pct`, `cold_nights_pct` — the notebook's **fixed-percentile companion metric** (a single station-wide 90th/10th percentile of `TMAX`/`TMIN` over the reference period), **not** the full calendar-day ETCCDI TX90p/TN10p climatology. `temp_func.py`'s method estimates a percentile per calendar day from a centred 5-day window with nested Python loops over the whole base period — fine for one station, far too slow for a few hundred. Do not describe `hot_days_pct`/`cold_nights_pct` as ETCCDI-equivalent; they are a simplified regional proxy.

### Required inputs
- `data/regional/<region_key>_stations.pkl` from `Regional/00_regional_setup.ipynb`.

### Workflow
1. Load the regional station dictionary for `region_key`.
2. `compute_regional_temperature_indicators(stations_data, ...)` → `(dict_lon_lat, annual_data, thresholds)`. Stations with no usable `TMIN`/`TMAX` (e.g. rainfall-only stations) are skipped automatically.
3. Build a per-station summary table: linear trend (per decade) + p-value of each indicator over its own period of record.
4. Save the computed indicators (pickle + long CSV + summary CSV, see Output contract).
5. **Regional-mean anomaly time series**: `compute_regional_temperature_anomaly_series(annual_data, ...)` — each station's own anomaly relative to the reference period, then a simple unweighted average across stations per year, with a 5-year centred rolling mean (solid = annual value, dashed = 5-year running mean).
6. **Regional maps** — one trend map per indicator via `plot_annual_regional_map` (EEZ base map, red/blue diverging colour scale centred on zero, `x` marker for stations significant at 95%). Same `RegionalMapConfig(min_years=20, ...)` guard as the rainfall notebook.
7. **ERA5 background maps — `tmean_annual` only.** ERA5 is opened as **monthly mean** 2 m temperature (`t2m`); a monthly mean is only enough to reconstruct the annual mean temperature (mean or trend) by averaging 12 months/year. `tmin_annual`, `tmax_annual`, `diff_annual` need daily min/max, and `hot_days_pct`/`cold_nights_pct` need a daily percentile-exceedance count — none of those exist in the monthly-mean ERA5 product, so no ERA5 background is produced for them. Cached under `data/regional/era5_cache/` (shared with the rainfall notebook's cache directory, different filenames).
8. **ERA5 EEZ-mean anomaly time series**: `plot_era5_eez_temperature_anomaly(...)` — the ERA5 counterpart of Step 5, but an **area-weighted** mean over the Pacific EEZ grid cells rather than a station average.

### Output contract
- `data/regional/<region_key>_temperature_indicators.pkl` — `{"dict_lon_lat", "annual_data", "thresholds"}`.
- `data/regional/<region_key>_temperature_indicators_annual.csv` — long format, one row per station × year.
- `data/regional/<region_key>_temperature_indicators_summary.csv` — one row per station, trend + p-value per indicator.
- `outputs/figures/regional_<region_key>/T_regional_<indicator>_trend_<region_key>.png` — one per indicator: `cold_nights_pct`, `diff_annual`, `hot_days_pct`, `tmax_annual`, `tmean_annual`, `tmin_annual`.
- `outputs/figures/regional_<region_key>/T_regional_mean_anomaly_timeseries_<region_key>.png` (station average) and `..._timeseries_era5_<region_key>.png` (EEZ area-weighted).
- `outputs/figures/regional_<region_key>/T_regional_tmean_annual_mean_era5_<region_key>.png` and `..._trend_era5_<region_key>.png`.

### Reporting style
- "Regional [indicator] trend across the Pacific EEZ area (`region_key`): station-level map, N stations, X significant at p < 0.05."
- Always disambiguate `hot_days_pct`/`cold_nights_pct` (fixed regional percentile proxy) from the National `c_hot_cold_days.ipynb`'s ETCCDI TX90p/TN10p when reporting both in the same conversation.
- State whether an anomaly series is the station-average or the ERA5 EEZ area-weighted version.

### Hard rules
- Do not reimplement the per-station formulas inline — always call `compute_regional_temperature_indicators` from `functions/rainfall_regional.py`.
- Do not add an ERA5 background to any indicator besides `tmean_annual`.
- Do not present `hot_days_pct`/`cold_nights_pct` as ETCCDI-equivalent to the National workflow's TX90p/TN10p — they use a different (simpler, faster) method by design.
