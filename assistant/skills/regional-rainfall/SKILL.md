---
name: regional-rainfall
description: Compute per-station regional rainfall indicators (total annual rainfall, dry/wet days, consecutive dry days, heavy rainfall) across every station in a region and build Pacific EEZ trend maps, with an optional ERA5 background for total annual rainfall. Use when working on notebooks/historical/Regional/rainfall/regional_indicators.ipynb or answering questions about Pacific-wide/regional rainfall maps or trends.
---

## Skill: Regional Rainfall Indicators (notebook `notebooks/historical/Regional/rainfall/regional_indicators.ipynb`)

### Purpose
For every station saved by `Regional/00_regional_setup.ipynb`, compute the **same rainfall indicators used at the single-site level** (`notebooks/historical/National/rainfall/`) and collect them into one regional dataset that can be mapped across the Pacific EEZ area. The per-station formulas live in `functions/rainfall_regional.py` (`_station_rainfall_indicators` / `compute_regional_rainfall_indicators`) — this notebook stays thin: load → compute → save → map.

### Indicator mapping to the National notebooks
- `a_Total_rainfall.ipynb` → `total_annual_mm` (count-normalised annual accumulation, same formula as the National notebook).
- `b_Consecutive_dry_days.ipynb` → `dry_days`, `max_consecutive_dry_days`, `mean_consecutive_dry_days`.
- `c_Heavy_rainfall.ipynb` → `wet_days`, `heavy_days` (each station's **own** 95th-percentile threshold, not a region-wide one).

### Required inputs
- `data/regional/<region_key>_stations.pkl` from `Regional/00_regional_setup.ipynb`.

### Workflow
1. Load the regional station dictionary for `region_key`.
2. `compute_regional_rainfall_indicators(stations_data, ...)` → `(dict_lon_lat, annual_data, heavy_thresholds)`. Stations with no usable `PRCP` (e.g. temperature-only stations) are skipped automatically.
3. Build a per-station summary table: linear trend (per decade) + p-value of each indicator over its own period of record — this is exactly what the Section 5 maps plot.
4. Save the computed indicators (pickle + long CSV + summary CSV, see Output contract).
5. **Regional maps** — one trend map per indicator via `plot_annual_regional_map` (EEZ base map, diverging colour scale centred on zero, `x` marker for stations significant at 95%). `RegionalMapConfig(min_years=20, ...)` guards against an unstable trend from a station with very few valid years dominating the colour scale.
6. **ERA5 background maps — `total_annual_mm` only.** ERA5 is opened as **monthly** total precipitation (`tp`); a monthly total is only enough to reconstruct the annual accumulated rainfall (mean or trend) by summing 12 months/year. The other five indicators (`dry_days`, `wet_days`, `max_consecutive_dry_days`, `mean_consecutive_dry_days`, `heavy_days`) are day-count/consecutive-run metrics that need **daily** precipitation and have no ERA5 counterpart — do not attempt to fabricate one. ERA5 mean/trend fields are cached as NetCDF under `data/regional/era5_cache/`; set `force_recompute_era5 = True` to refresh.

### Output contract
- `data/regional/<region_key>_rainfall_indicators.pkl` — `{"dict_lon_lat", "annual_data", "heavy_thresholds"}`.
- `data/regional/<region_key>_rainfall_indicators_annual.csv` — long format, one row per station × year.
- `data/regional/<region_key>_rainfall_indicators_summary.csv` — one row per station, trend + p-value per indicator.
- `outputs/figures/regional_<region_key>/R_regional_<indicator>_trend_<region_key>.png` — one per indicator: `dry_days`, `heavy_days`, `max_consecutive_dry_days`, `mean_consecutive_dry_days`, `total_annual_mm`, `wet_days`.
- `outputs/figures/regional_<region_key>/R_regional_total_annual_mm_mean_era5_<region_key>.png` and `..._trend_era5_<region_key>.png`.

### Reporting style
- "Regional [indicator] trend across the Pacific EEZ area (`region_key`): station-level map, N stations, X significant at p < 0.05."
- State whether a map is station-only or has an ERA5 background, and that ERA5 background only exists for `total_annual_mm`.

### Hard rules
- Do not reimplement the per-station formulas inline — always call `compute_regional_rainfall_indicators` from `functions/rainfall_regional.py` so regional and National numbers can never silently diverge.
- Do not add an ERA5 background to any indicator besides `total_annual_mm` — the underlying monthly ERA5 field cannot support the others.
- Use `min_years=20` (or whatever `Regional/00_regional_setup.ipynb`'s `min_years_after_filter` was set to) consistently between the setup and mapping steps.
