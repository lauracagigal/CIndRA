---
name: national-rainfall
description: "Compute and maintain the complete National rainfall workflow for one configured GHCN-Daily station: annual and seasonal totals, anomalies, ENSO context, dry-day counts and consecutive dry spells, wet-day counts, and heavy rainfall above the 95th percentile. Use for any notebook under notebooks/historical/National/rainfall/ or questions about site-scale rainfall indicators."
---

# National rainfall

Use this skill for the three National rainfall notebooks. Reuse their shared site configuration, cached `PRCP` record, plotting helpers, and persistence conventions instead of rebuilding those steps separately.

## Inputs and shared setup

- Run `notebooks/historical/National/00_site_setup.ipynb` first.
- Load `data/sites/<site_key>.json` with `load_site_config` and `site_config_filename`.
- Load `data/rainfall/GHCN_<ghcn_station_id>.pkl`; never download or completeness-filter GHCN again inside an indicator notebook.
- Build output paths with the helpers in `functions/site_common.py` or their `functions/rainfall.py` re-exports.
- Use the reference period and completeness threshold stored in the site config. Do not hardcode Palau values for another site.

## Route by notebook

### Total and seasonal rainfall

Notebook: `rainfall/a_Total_rainfall.ipynb`.

1. Retain the daily `PRCP` series for daily maxima and ENSO joins.
2. Normalize annual accumulated rainfall for unequal valid-day counts:

   `annual mm = annual observed sum / annual valid-day count * 365`

3. Calculate anomalies against `datag.loc[ref_start:ref_end].PRCP.mean()`; use a range slice, not a single `"1961:1990"` label.
4. Plot annual totals and their trend with `plot_bar_probs`; multiply its annual slope by 10 for **mm/decade**.
5. Report the ten wettest years and plot accumulated-rainfall anomalies.
6. Calculate wet/dry seasonal totals only after confirming the site's season definitions. The notebook's Palau convention is wet May–October and dry November–April.
7. When requested, join monthly rainfall to NOAA ONI and use `add_oni_cat` plus `plot_bar_probs_ONI`.
8. Build `table_rain_21` and persist with `persist_total_rainfall_outputs`.

Canonical figures: `F5_Rain_accum.png`, `F5_Rain_anom_top10.png`, `F5_Rain_mean_ONI_daily.png`, `F5_Rain_mean_ONI_accum.png`, `F6a_Rain_dry_season.png`, and `F6a_Rain_wet_season.png`.

### Dry days and consecutive dry spells

Notebook: `rainfall/b_Consecutive_dry_days.ipynb`.

1. Use a **1 mm** threshold and state the exact comparison used by the notebook when reporting boundary values.
2. Calculate annual dry-day counts.
3. Call `consecutive_dry_days` for the annual maximum spell and `count_consecutive_days` for the running daily spell; do not reimplement either helper.
4. Plot annual counts and maximum spells with `plot_bar_probs`; report trends in **days/decade**.
5. Build `table_rain_22` and persist with `persist_dry_days_outputs`.

Canonical figures: `F6a_Number_dry.png` and `F6b_Consecutive_dry.png`.

### Wet and heavy-rainfall days

Notebook: `rainfall/c_Heavy_rainfall.ipynb`.

1. Calculate annual wet-day counts using the notebook's 1 mm convention.
2. Calculate the station threshold as the 95th percentile of non-missing `PRCP` over the **full available record**, rounded to two decimals.
3. Count annual days above that threshold and keep the 1 mm and 95th-percentile populations explicitly labelled.
4. Plot both series with `plot_bar_probs`; report trends in **days/decade** and the computed threshold in **mm**.
5. Build `table_rain_23` and persist with `persist_heavy_rainfall_outputs`.

Canonical figures: `F7a_Wet_days_1mm.png` and `F7b_Wet_days_95p.png`.

## Common plotting and reporting rules

- Discover and import `plot_bar_probs`, `plot_bar_probs_ONI`, `add_oni_cat`, and `plot_timeseries_interactive` as described in `../functions-api/SKILL.md`; do not redefine them inline.
- Label a custom matplotlib fallback as a quick-look figure, not repository styling.
- Report station ID and name, GHCN-Daily source, analysis window, units, reference period, completeness filtering, trend and p-value where available.
- Distinguish **mm/day**, **mm/year**, **mm/decade**, event **days/year**, and **days/decade**.
- Follow `../output-conventions/SKILL.md` for every persisted artifact.
