---
name: functions-api
description: Full reference of callable functions across functions/site_common.py, rainfall.py, air_temp.py, temp_func.py, data_downloaders.py, rainfall_regional.py, sea_level.py, sea_level_plotting.py, and the external indicators_setup package, plus the function-discovery workflow. Use before writing any analysis or plotting code, to find and reuse an existing function instead of reimplementing it inline.
---

## Skill: Functions API Reference (`functions/site_common.py` + `functions/rainfall.py` + `functions/air_temp.py` + `functions/temp_func.py` + `functions/data_downloaders.py` + `functions/rainfall_regional.py` + `functions/sea_level.py` + `functions/sea_level_plotting.py` + `indicators_setup`)

Single source of truth for what the assistant is allowed to call, across the rainfall, air-temperature, and sea-level workflows. If something is missing, add a function to `functions/` — do not inline it in notebooks.

---

## Function-Discovery Rule

CIndRA should actively **find and use functions from the relevant repositories** before writing custom analysis or plotting code.

For PICCM plotting and styling (rainfall and air temperature alike), look for and use functions from the external **`indicators_setup`** repository:

- GitHub: <https://github.com/lauracagigal/indicators_setup>
- Package path: `ind_setup`
- Canonical plotting module: `ind_setup.plotting`
- Canonical styled bar-plot function: `plot_bar_probs`
- Canonical interactive time-series function: `plot_timeseries_interactive` (`ind_setup.plotting_int`)

`plot_bar_probs` is the preferred helper for published PICCM bar charts: accumulated annual rainfall, dry-day counts, consecutive dry-day metrics, wet-day counts, heavy-rainfall counts, and annual mean-temperature trends. `plot_timeseries_interactive` is preferred for annual TMIN/TMAX, diurnal range, and hot-day/cold-night time series.

**Sea level does not use `indicators_setup` at all.** Its plotting/styling is entirely repository-local in `functions/sea_level_plotting.py`, and its calculations live in `functions/sea_level.py`. Do not search `indicators_setup` for sea-level helpers; go straight to those two modules (see the dedicated sections below).

---

## Function Discovery Workflow

When a required function is not immediately importable, search the local workspace and known repositories before falling back to ad-hoc code.

### 1. Try direct imports first

```python
from ind_setup.plotting import plot_bar_probs
from ind_setup.plotting import plot_bar_probs_ONI
from ind_setup.plotting import add_oni_cat
from ind_setup.plotting_int import plot_timeseries_interactive, fig_int_to_glue
from ind_setup.tables import style_matrix
from ind_setup.tables import table_rain_21, table_rain_22, table_rain_23
from ind_setup.tables import table_temp_11, table_temp_12, table_temp_13, table_temp_13b
```

If imports succeed, inspect the function signature before calling unfamiliar functions.

### 2. Search the local workspace

Search bounded local paths:

- `ind_setup/plotting.py`
- `ind_setup/colors.py`
- `ind_setup/tables.py`
- `indicators_setup/ind_setup/plotting.py`
- `functions/site_common.py`
- `functions/rainfall.py`
- `functions/air_temp.py`
- `functions/temp_func.py`
- `functions/data_downloaders.py`
- `functions/rainfall_regional.py`
- `functions/sea_level.py`
- `functions/sea_level_plotting.py`

Look for: `plot_bar_probs`, `plot_bar_probs_ONI`, `plot_timeseries_interactive`, `add_oni_cat`, `get_df_col`, `style_matrix`, `table_rain_21`, `table_rain_22`, `table_rain_23`, `table_temp_11`, `table_temp_12`, `table_temp_13`, `table_temp_13b` (rainfall/air-temperature); any of the functions listed in the `sea_level.py`/`sea_level_plotting.py` sections below (sea level).

Notebooks typically add the package via `sys.path.append("../../../../../../indicators_setup")` (rainfall/air-temperature analysis notebooks under `notebooks/historical/National/<domain>/`, four levels deeper than the repository root, six levels from `indicators_setup`). Sea-level notebooks do not add `indicators_setup` to `sys.path` at all — they only need `sys.path.append("../../../../functions")`.

### 3. Clone `indicators_setup` if missing

If `indicators_setup` is not installed and not present locally, clone into a session-local folder such as `external/indicators_setup`, then add the repository root to `sys.path` so `ind_setup` can be imported.

Do **not** assume the repository is pip-installable. It may lack `setup.py` or `pyproject.toml`; cloning and path injection may be required.

### 4. Use repository functions once found

- `plot_bar_probs(..., trendline=True, return_trend=True)` — styled bar plots with linear trend lines.
- `plot_timeseries_interactive(dict_plot, trendline=True, return_trend=True)` — styled interactive plotly time series, single- or multi-series.
- Use the trend returned by these functions when reporting the repository-computed trend.
- If p-value or additional regression statistics are needed and not returned by the plotting function, compute those separately only for reporting, while preserving the repository-generated figure style.

---

## `plot_bar_probs` signature and usage

Expected signature:

`plot_bar_probs(x, y, bar_label=None, labels=None, trendline=False, y_label=' ', figsize=[7, 5], return_trend=False)`

Returns `(fig, ax)` or `(fig, ax, trend)` when `return_trend=True`.

| Use case | `x` | `y` | `y_label` | Trend units |
|---|---|---|---|---|
| Accumulated annual rainfall | years (numeric) | mm/year | `Accumulated annual rainfall (mm/year)` | mm/year → ×10 for mm/decade |
| Dry-day counts | years | days/year | `Number of dry days` | days/year → ×10 for days/decade |
| Wet-day / heavy-day counts | years | days/year | as appropriate | days/year → ×10 for days/decade |
| Annual mean temperature | years | °C | `Mean Temperature` | °C/year → ×10 for °C/decade |

Ad-hoc matplotlib bar plots are acceptable only for quick-look/QC or when `plot_bar_probs` is truly unavailable after discovery. Label such outputs as quick-look or non-repo-styled.

---

## `functions/site_common.py` — shared site config, output paths

`rainfall.py` and `air_temp.py` both re-export everything in this module (`from rainfall import site_config_filename` and `from air_temp import site_config_filename` are the same function) -- it exists so the two domain modules don't maintain two silently-diverging copies of the same code. Import from whichever domain module matches the notebook; there is no reason to import `site_common` directly.

`sea_level.py` also imports `save_site_config`, `build_site_tag`, `build_output_filename`, and `save_dict_json` from this module (identical logic, single source of truth after the PICCM_Atmosphere/PICCM_SeaLevel merge deduplication) — but keeps its **own** `load_site_config` (error message points at the sea-level setup notebook, not `00_site_setup.ipynb`) and its own `save_table_to_csv` (defaults to `index=False`, vs. `site_common.save_table_to_csv`'s `index=True` default). Do not "fix" `sea_level.py`'s `save_table_to_csv` default to match `site_common.py` — sea-level notebooks depend on `index=False`.

**Site configuration**
- `site_config_filename(site_key)` → JSON filename (slugified: lowercase, non-alphanumeric → `_`). `site_key` is normally `<country_slug>_<ghcn_station_id>`, e.g. `"palau_PSW00040309"` → `"palau_psw00040309.json"`.
- `save_site_config(config_dict, output_path)` → write site JSON; creates parent directory.
- `load_site_config(config_path)` → load JSON dict. Raises `FileNotFoundError` if missing.
- `list_available_sites(sites_dir)` → DataFrame, one row per `data/sites/*.json`, columns `site_key`, `site_name`, `country`, `ghcn_station_id`, `ghcn_station_name`, `vars_interest`. Call before asking the user for a `site_key` so they can reuse an already-configured site.

**Output paths**
- `build_site_tag(site_name, site_lon, site_lat)` → filesystem-safe tag.
- `build_output_filename(base_name, site_name, site_lon, site_lat, ext='png')` → `"<base_name>_<site_tag>.<ext>"`.
- `build_site_figures_dir(base_outputs_dir, ...)` → `outputs/figures/<site_tag>/`.
- `build_site_tables_dir(base_outputs_dir, ...)` → `outputs/tables/<site_tag>/`.

**Persist-helper internals** (used by the `persist_*_outputs` functions below, not usually called directly): `table_to_dataframe`, `save_table_to_csv`, `save_dict_json`, `_trend_pvalue`, `_series_stats`, `_site_meta`, `_frame_with_year_column`, `_display_site_table`.

---

## `functions/rainfall.py` and `functions/air_temp.py` — domain-specific persist helpers

**Rainfall-specific (`rainfall.py`), dry-spell metrics** (notebook `b_Consecutive_dry_days.ipynb`)
- `consecutive_dry_days(series)` → maximum consecutive dry days in a boolean series.
- `count_consecutive_days(series)` → running count of consecutive dry days.

**Persist helpers**
- `rainfall.py`: `persist_total_rainfall_outputs(...)` (`a_Total_rainfall.ipynb`: CSVs + `R_mean_summary_metrics_*.json`), `persist_dry_days_outputs(...)` (`b_Consecutive_dry_days.ipynb`: CSVs + `R_dry_summary_metrics_*.json`), `persist_heavy_rainfall_outputs(...)` (`c_Heavy_rainfall.ipynb`: CSVs + `R_heavy_summary_metrics_*.json`).
- `air_temp.py`: `persist_mean_temperature_outputs(...)` (`a`: CSVs + `T_mean_summary_metrics_*.json`), `persist_minmax_temperature_outputs(...)` (`b`: CSVs + `T_minmax_summary_metrics_*.json`), `persist_hot_cold_outputs(...)` (`c`: CSVs + `T_hot_cold_summary_metrics_*.json`).

Station ranking/selection in the atmosphere `00_site_setup.ipynb` is currently a plain alphabetical station table (`sort_values(["Name", "ID"])`) — there is no distance-based ranking helper for GHCN stations in `functions/`. (Sea level's `select_uhslc_station` in `sea_level.py` *does* rank by distance via an internal `_haversine_km` — that one is real and in active use; do not confuse it with the removed atmosphere-side dead code.)

---

## `functions/temp_func.py` — ETCCDI temperature-extreme calculations

- `exceedance_rate_for_base_period(st_data, var)` → per-year exceedance rate over the 1961–1990 base period for `"TMAX"` (TX90p) or `"TMIN"` (TN10p).
- `exceedance_rate_for_outbase_period(st_data, var)` → calendar-day (366-row) percentile thresholds `(DAY, THRESHOLD)` derived from the base period, applied to the full record.

---

## `functions/data_downloaders.py` — GHCN, ONI, completeness

**`GHCN` class**
- `download_country_codes()` → DataFrame `(Code, Country)`.
- `get_country_code(country)` → exact-match row(s) for a country name.
- `download_stations_info()` → `ID`, `Latitude`, `Longitude`, `Elevation`, `Name`.
- `download_station_inventory()` → per-station element record spans.
- `summarize_record_years(inventory_df, station_ids, elements=("TMIN", "TMAX", "PRCP"))` → `record_start`, `record_end`, `record_years`, `elements`.
- `extract_dict_data_var(GHCND_dir, var, df_country_stations)` → `(records, station_ids)`. Downloads per-station CSV; divides `TMIN`/`TMAX`/`PRCP` by 10. Returns plot-ready dicts plus ID list.

**Standalone functions**
- `download_oni_index(url)` → monthly ONI DataFrame; `-99.9` → NaN. Used by rainfall, air-temperature, *and* sea-level notebooks.
- `filter_by_time_completeness(df, time_col, month_threshold, year_threshold)` → `(df_filtered, removed_months, removed_years)`.
- `download_uhslc_data(data_dir, uhslc_id, resolution="daily")` → `Path` to the cached UHSLC NetCDF (`d<uhslc_id>.nc` / `h<uhslc_id>.nc`, zero-padded to 3 digits). **Cache lookup only** — raises `FileNotFoundError` (with the exact expected path and a manual-download pointer to `https://uhslc.soest.hawaii.edu/data/?rq`) if the file isn't already cached under `data/sea_level/`. Automatic download was lost when this module was merged from the two source repos (the atmosphere-only version silently overwrote the sea-level one) and has not been restored — do not claim it fetches new stations.

---

## `functions/rainfall_regional.py` — regional (multi-station) Pacific maps

Used by `notebooks/historical/Regional/rainfall/regional_indicators.ipynb` and `notebooks/historical/Regional/air_temperature/regional_indicators.ipynb`, both of which build on the multi-station dictionary `notebooks/historical/Regional/00_regional_setup.ipynb` produces (`data/regional/<region_key>_stations.pkl`). Not part of the single-site `00_site_setup.ipynb` → `a/b/c` workflow the rest of this file describes, and not related to sea level (there is no regional sea-level workflow yet — see `cindra_regional_plotting_helpers.py` below).

**Regional indicators** (per-station annual DataFrames, mirroring the National single-site notebooks' formulas)
- `compute_regional_rainfall_indicators(stations_data, ...)` → `(dict_lon_lat, annual_data, heavy_thresholds)`. Columns: `total_annual_mm`, `dry_days`, `wet_days`, `max_consecutive_dry_days`, `mean_consecutive_dry_days`, `heavy_days` (`RAINFALL_INDICATOR_LABELS`/`RAINFALL_INDICATOR_UNITS`).
- `compute_regional_temperature_indicators(stations_data, ...)` → `(dict_lon_lat, annual_data, thresholds)`. Columns: `tmean_annual`, `tmin_annual`, `tmax_annual`, `diff_annual`, `hot_days_pct`, `cold_nights_pct` (`TEMPERATURE_INDICATOR_LABELS`/`TEMPERATURE_INDICATOR_UNITS`). `hot_days_pct`/`cold_nights_pct` use a **fixed station-wide percentile** (90th `TMAX` / 10th `TMIN` over the reference period), not the full calendar-day ETCCDI TX90p/TN10p climatology in `temp_func.py` — that method is too slow to run per-station across a few hundred stations.
- `compute_regional_temperature_anomaly_series(annual_data, ...)` → `(annual_anomaly, smoothed)`, a simple unweighted station-average anomaly time series with a 5-year rolling mean.

**Station-only maps** (no ERA5)
- `RegionalMapConfig(variable, metric="trend"|"mean", period_start, period_end, min_years=2, cmap, vmin, vmax, color_label, ...)` — `min_years` guards against an unstable few-point regression (e.g. 2 valid years) dominating a map's colour scale; the regional notebooks set it to 20.
- `build_sites_map_dataframe(dict_lon_lat, config, annual_data=...)` → one row per station: `value`, `p_value`, `n_years`, `significant`.
- `plot_annual_regional_map(dict_lon_lat, annual_data, data_dir, config, variable_labels=...)` → `(fig, ax, sites_df)`. `data_dir` here is this repo's own `data/regional/` folder, which holds `Pacific_EEZs/*.shp`.
- `create_pacific_base_map(data_dir, ...)` → `(fig, ax, eez_gdf)`, the shared EEZ + land base map both regional notebooks build on.

**ERA5-background maps** — only for indicators reconstructable from *monthly* ERA5 fields (annual accumulated rainfall, annual mean temperature); anything needing daily data (dry-day counts, hot/cold days, diurnal range) has no ERA5 counterpart.
- `plot_monthly_rainfall_with_era5_background(dict_lon_lat, monthly_data, data_dir, era5_ds, metric=..., annual_data=..., variable="total_annual_mm", era5_field=..., min_years=...)` / `plot_monthly_temperature_with_era5_background(..., variable="tmean_annual", ...)` — pass exactly one of `monthly_data` (CIPSAP-style) or `annual_data` (GHCN-style, this repo's usage); `era5_field` lets a caller pass an already-computed field to skip recomputation.
- `load_or_compute_era5_annual_rainfall(era5_ds, cache_path, metric, ...)` / `load_or_compute_era5_annual_temperature(...)` — NetCDF-cached mean/trend field computation (pulling + aggregating global monthly ERA5 over the network is slow); pass `era5_ds=None` on a cache hit.
- `plot_era5_eez_temperature_anomaly(era5_ds, data_dir, period_start, period_end, baseline_start, baseline_end, smooth_years=5)` → EEZ area-weighted mean temperature anomaly time series (the ERA5 counterpart of `compute_regional_temperature_anomaly_series`'s station average).
- ERA5 endpoint: `https://api.earthdatahub.destine.eu/era5/era5-single-levels-atmosphere-monthly-v0.zarr` (opened with `xarray.open_dataset(..., engine="zarr")`); `tp` needs `* 1000 * 30` (m/day → mm/month) and an explicit `.attrs["units"] = "mm"` before use, `t2m` needs `- 273.15` (K → °C).

---

## `functions/sea_level.py` — sea-level calculations, station selection, persistence

Used by all four sea-level notebooks (`0_site_setup.ipynb` through `d_sea_level_rankings.ipynb`). Not part of the atmosphere `site_common.py`/`rainfall.py`/`air_temp.py` family, though it re-uses four of `site_common.py`'s functions directly (see the `site_common.py` note above) rather than keeping fully independent copies.

**Data acquisition / station selection**
- `get_CMEMS_data(data_dir, minlon, maxlon, minlat, maxlat, start_date_str, end_date_str)` → cached CMEMS L4 SSH NetCDF path (downloads via `copernicusmarine` on a cache miss).
- `select_uhslc_station(site_lon, site_lat, station_country_filter=None, selected_uhslc_id=None, selected_station_name=None, ...)` → nearest/matching UHSLC station dict, querying `https://uhslc.soest.hawaii.edu/data/meta.geojson`.
- `get_uhslc_datum(uhslc_id, datum_name)` → `(datum_value_mm, datum_table)` for a UHSLC station (e.g. `"MSL"`, `"MHHW"`).
- `prepare_site_data(site_config, data_dir)` → resolves the UHSLC station, updates the config, and pre-downloads UHSLC (via `download_uhslc_data` in `data_downloaders.py`) + ONI + CMEMS data. Called once from `0_site_setup.ipynb`.

**Trend fitting**
- `process_trend_with_nan(sea_level_anomaly)` → `(trend_mag, sea_level_trend, trend_rate, p_value, trend_err)` for an `xarray.DataArray`, preserving NaNs.
- `process_trend_single_series(data, var)` → `(coefficients, trendline, trend_per_year)` via `np.polyfit` on a single `xarray` variable.
- `get_trend_info(x, y, timescale="days")` → `(trend_counts, trend_label, linestyle_trend, slope, p_value)` for flood-count trend chips.

**ENSO**
- `detect_enso_events(oni_df)` → adds `ONI Mode` (`"El Nino"`/`"La Nina"`/`"Neutral"`), `year_storm`, `El Nino`, `La Nina` columns. El Niño/La Niña require 5 consecutive months with `ONI > 0.5` / `< -0.5`.
- `get_dominant_enso(series)` → majority ENSO mode in a grouped series.

**Rankings**
- `get_top_ten(rsl, record_id, mode="max"|"min")` → top/bottom 10 events at least 3 days apart.
- `get_top_10_table(rsl, record_id)` → combined top-10 high/low table joined with the nearest-month ONI state.

**Summary tables / persistence**
- `build_enso_summary_table(slope, nino_1997, nina_1998, r_value, p_value)`, `build_sl_magnitude_results(...)` → styled summary DataFrames for the trend notebook.
- `save_site_config`, `load_site_config`, `build_site_tag`, `build_output_filename`, `save_table_to_csv`, `save_dict_json` — see the `site_common.py` note above for which of these are re-used vs. kept local.

---

## `functions/sea_level_plotting.py` — every sea-level figure

The sea-level equivalent of `indicators_setup`: **every** published sea-level figure comes from here, not from ad-hoc matplotlib/plotly code. If a new sea-level chart type is needed, add it here first.

- **Maps**: `plot_map`, `plot_map_base`, `plot_station_vs_grid_map`, `plot_magnitude_map`, `plot_magnitude_map_background`, `plot_anomaly_decadal_maps`, `add_zebra_frame`/`plot_zebra_frame` (map border styling), `pacific_all_west_formatter` (Pacific-centric longitude tick labels — required on any decadal/regional map).
- **Trend timeseries**: `plot_altimetry_scatter`, `plot_altimetry_trend_timeseries`, `plot_tide_gauge_scatter`, `plot_tide_gauge_trend_timeseries`, `plot_combined_trends` (single-panel altimetry + tide-gauge comparison), `plot_enso_scatter` (ENSO sensitivity scatter + regression).
- **Anomaly**: `plot_tg_rsl_anomaly_annual`, `plot_anomaly_station_series`, `plot_annual_range_fill`.
- **Flood frequency**: `plot_histogram_with_threshold`, `plot_flood_counts_with_trend`, `plot_flood_counts_with_oni`, `plot_flood_days_heatmap`, `plot_flood_matrix_summary`, `plot_flood_count_per_year`, `plot_trend`, `plot_oni_segments`, `plot_oni_only`, `plot_monthly_contribution`, `plot_monthly_contribution_vertical`, `plot_simple_timeseries`, `plot_daily_max_timeseries`.
- **Rankings**: `style_oni_based` (pandas Styler row-coloring by ONI mode), `make_plotly_figure_rankings`, `make_rankings_static_figure`.

---

## `functions/cindra_regional_plotting_helpers.py` — draft, not wired into any notebook

Two regional sea-level plotting helpers prepared ahead of a not-yet-built regional sea-level workflow: `plot_regional_altimetry_trend_map_filled_tide_gauges` (gridded absolute altimetry trend + optional filled tide-gauge markers) and `plot_regional_flood_frequency_overview` (station-year flood-day heatmap + regional annual totals). The module docstring marks them "Draft / Experimental"; `grep` confirms no notebook imports them. `notebooks/historical/Regional/regional_plots.ipynb` is the presumed future consumer, but it is currently an empty file (0 bytes). Do not present output from these two functions as a published/repo-styled figure until they are actually wired into a notebook and reviewed — treat a request to use them the same as "the helper doesn't exist yet."

---

## External plotting / tables (`indicators_setup`, rainfall/air-temperature only)

- `ind_setup.plotting`: `plot_bar_probs`, `plot_bar_probs_ONI`, `add_oni_cat`, `plot_oni_index_th`, `fontsize`.
- `ind_setup.plotting_int`: `plot_timeseries_interactive`, `fig_int_to_glue`.
- `ind_setup.tables`: `style_matrix`, `table_rain_21`, `table_rain_22`, `table_rain_23`, `table_temp_11`, `table_temp_12`, `table_temp_13`, `table_temp_13b`.
- `ind_setup.colors`: `get_df_col` (stacked bar colours).

---

## Hard rules

- Never redefine helpers that exist in `functions/site_common.py`, `functions/rainfall.py`, `functions/air_temp.py`, `functions/temp_func.py`, `functions/data_downloaders.py`, `functions/rainfall_regional.py`, `functions/sea_level.py`, or `functions/sea_level_plotting.py`.
- Use repository functions before custom code; clone `indicators_setup` if missing (rainfall/air-temperature only — sea level has no external plotting dependency to clone).
- Do not fabricate repository functions or claim repo styling was used unless the function was actually imported and called.
- Do not claim `download_uhslc_data` downloads a new station's data — it only serves an already-cached local file.
- Do not present output from `functions/cindra_regional_plotting_helpers.py` as a finished/published figure — it is draft code not wired into any notebook.
- After editing modules, reload in the notebook: `import importlib; import rainfall as rf; importlib.reload(rf)` (or `air_temp`, `temp_func`, `rainfall_regional`, `sea_level`, `sea_level_plotting`).
- Keep this file in sync when `functions/` or `indicators_setup` usage changes.
