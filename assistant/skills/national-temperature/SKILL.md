---
name: national-temperature
description: "Compute and maintain the complete National air-temperature workflow for one configured GHCN-Daily station: annual mean temperature and anomalies, TMIN/TMAX and diurnal range, hot-day TX90p and cold-night TN10p extremes, trends, top years, and ENSO context. Use for any notebook under notebooks/historical/National/air_temperature/ or questions about site-scale temperature indicators."
---

# National air temperature

Use this skill for all three National temperature notebooks. Keep their common setup, cached data, plotting functions and output paths consistent.

## Inputs and shared setup

- Run `notebooks/historical/National/00_site_setup.ipynb` first.
- Load `data/sites/<site_key>.json`, then `data/air_temp/GHCN_<ghcn_station_id>.pkl`.
- Verify a `DatetimeIndex` and the required `TMIN`, `TMAX`, `TMEAN`, and `diff` columns.
- Preserve a daily copy before annual resampling.
- Use the configured reference period and output-path helpers. Do not re-download GHCN or redefine site values in indicator notebooks.

## Route by notebook

### Annual mean temperature

Notebook: `air_temperature/a_mean_temperature.ipynb`.

1. Resample `TMEAN` to annual means.
2. Use `plot_bar_probs` for the published annual trend; report the slope in **°C/decade**.
3. Calculate `TMEAN_ref = TMEAN - mean(TMEAN[ref_start:ref_end])` and identify the ten warmest anomaly years.
4. For ENSO context, join monthly station values to NOAA ONI and use `add_oni_cat` plus `plot_bar_probs_ONI`.
5. Persist the mean-temperature figures, ENSO summary CSV, and `T_mean_summary_metrics` JSON.

Canonical figures: `F2_ST_Mean.png` and `F2_ST_Annomalies_top10.png`.

### Minimum, maximum and diurnal range

Notebook: `air_temperature/b_min_max_temperature.ipynb`.

1. Use `plot_timeseries_interactive` for daily and annual `TMIN` and `TMAX` series.
2. Plot annual `TMIN` and `TMAX` together on a shared y-axis so their trends remain visually comparable.
3. Treat `diff = TMAX - TMIN` as the diurnal temperature range and plot its annual trend separately.
4. Persist HTML and PNG versions plus `T_minmax_summary_metrics` JSON.

Canonical figures: `F3_ST_min.html/.png`, `F3_ST_max.html/.png`, and `F3_ST_min_max.html/.png`.

### Hot days and cold nights

Notebook: `air_temperature/c_hot_cold_days.ipynb`.

1. For ETCCDI-style results, use `exceedance_rate_for_base_period` and `exceedance_rate_for_outbase_period` from `functions/temp_func.py`.
2. Define TX90p from calendar-day `TMAX` 90th-percentile thresholds and TN10p from calendar-day `TMIN` 10th-percentile thresholds over the configured base period.
3. Keep the notebook's simpler station-wide fixed-percentile companion metric separately labelled; never present it as identical to the calendar-day ETCCDI method.
4. Plot hot and cold counts with `plot_timeseries_interactive` and persist both interactive and static outputs plus the extremes summary metrics.

Canonical figures: `F4_ST_hot_cold.html/.png` and `F4_ST_hot_cold_percentiles.html/.png`.

## Common plotting and reporting rules

- Reuse `plot_bar_probs` and `plot_timeseries_interactive`; follow `../functions-api/SKILL.md` before adding plotting code.
- Report station ID and name, GHCN-Daily source, analysis period, configured reference period, completeness filtering and units.
- Report trends in **°C/decade** and distinguish annual mean values from daily extremes and event counts.
- Report `TMIN` and `TMAX` together when discussing asymmetric warming.
- Follow `../output-conventions/SKILL.md` for saved HTML, PNG, CSV and JSON files.
