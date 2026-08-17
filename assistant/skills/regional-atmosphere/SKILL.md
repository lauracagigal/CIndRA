---
name: regional-atmosphere
description: Compute and maintain Regional Pacific rainfall and air-temperature indicators from the multi-station GHCN dataset, including station summaries, EEZ trend maps, regional temperature anomaly series, and the limited ERA5 backgrounds supported by monthly data. Use for either regional_indicators.ipynb under Regional/rainfall or Regional/air_temperature, or questions about Pacific-wide atmosphere maps and trends.
---

# Regional atmosphere indicators

Use this skill for the parallel Regional rainfall and temperature notebooks. Both follow the same load → compute → summarize → persist → map workflow and use `functions/rainfall_regional.py`.

## Shared inputs and workflow

1. Run `notebooks/historical/Regional/00_regional_setup.ipynb` first.
2. Load `data/regional/<region_key>_stations.pkl`.
3. Call the domain-specific regional computation helper; never reproduce National formulas inline.
4. Create one station × year dataset and a station summary containing per-decade trends and p-values.
5. Persist pickle, long CSV and summary CSV before plotting.
6. Use `plot_annual_regional_map` with an EEZ base map, a diverging colour scale centred on zero, significance markers at `p < 0.05`, and `RegionalMapConfig(min_years=20, ...)` unless setup used another threshold.
7. Save figures beneath `outputs/figures/regional_<region_key>/`.

## Rainfall branch

Notebook: `Regional/rainfall/regional_indicators.ipynb`.

- Call `compute_regional_rainfall_indicators`.
- Map `total_annual_mm`, `dry_days`, `wet_days`, `max_consecutive_dry_days`, `mean_consecutive_dry_days`, and `heavy_days`.
- Produce an ERA5 mean or trend background only for `total_annual_mm`. Monthly ERA5 precipitation cannot reconstruct daily counts, consecutive spells or percentile-event metrics.
- Report whether a figure is station-only or includes ERA5 context.
- Persist `<region_key>_rainfall_indicators.pkl`, annual and summary CSVs, `R_regional_<indicator>_trend_<region_key>.png`, and the supported ERA5 total-rainfall maps.

## Temperature branch

Notebook: `Regional/air_temperature/regional_indicators.ipynb`.

- Call `compute_regional_temperature_indicators`.
- Map `tmean_annual`, `tmin_annual`, `tmax_annual`, `diff_annual`, `hot_days_pct`, and `cold_nights_pct`.
- Describe `hot_days_pct` and `cold_nights_pct` as fixed station-wide percentile proxies, not as the National calendar-day ETCCDI TX90p/TN10p method.
- Use `compute_regional_temperature_anomaly_series` for the unweighted station-average anomaly and distinguish it from the area-weighted ERA5 EEZ anomaly.
- Produce an ERA5 background only for `tmean_annual`; monthly mean ERA5 cannot reconstruct daily min/max or threshold counts.
- Persist `<region_key>_temperature_indicators.pkl`, annual and summary CSVs, `T_regional_<indicator>_trend_<region_key>.png`, regional anomaly series, and the supported ERA5 mean-temperature maps.

## Common safeguards

- Skip stations without the variables required by the selected branch.
- Keep `region_key`, `min_years`, analysis periods, units and significance criteria explicit.
- Do not compare station-average and ERA5 area-weighted series as though they used the same sampling.
- Keep the ERA5 cache under `data/regional/era5_cache/` and use `force_recompute_era5` only when a refresh is intended.
- Consult `../functions-api/SKILL.md`, `../data-sources/SKILL.md`, and `../output-conventions/SKILL.md` for shared implementation details.
