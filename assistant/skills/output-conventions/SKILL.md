---
name: output-conventions
description: Defines the site-tag, filename, and folder conventions for every persisted figure/table/JSON across rainfall, air-temperature, tropical-cyclone, and sea-level notebooks, so outputs never collide. Use whenever saving a new figure, table, or metrics file, or when asked where a given output file lives.
---

## Skill: Output Conventions

All persisted artifacts (figures, tables, structured results) MUST follow this convention so multi-site analyses never collide. The site-tag/filename scheme applies to **all three** domains (rainfall, air-temperature, sea level); the folder layout differs slightly for sea level (see below).

See [assets/example_output_tree.txt](assets/example_output_tree.txt) for a real, already-run example of every folder/filename pattern below side by side (rainfall+temperature site, sea-level site, and regional).

### Site tag

- Build with `build_site_tag(site_name, site_lon, site_lat)`.
- Format: `<lowercase_alphanum_site>_lat<lat3dec>p<dec>_lon<lon3dec>p<dec>`.
- Example: `palau_PSW00040309` (134.477, 7.337) → `palau_psw00040309_lat7p337_lon134p477`.

### Filenames

- Build with `build_output_filename(base_name, site_name, site_lon, site_lat, ext=...)`.
- Default extensions: `png` (matplotlib figures), `html` (plotly), `csv` (tables), `json` (metrics).

### Folders — rainfall / air temperature

```
outputs/
├── figures/<site_tag>/     # all published figures
└── tables/<site_tag>/      # CSV tables + JSON metrics
```

- Figures: `build_site_figures_dir(Path('../../../../outputs'), ...)`.
- Tables: `build_site_tables_dir(Path('../../../../outputs'), ...)` (via `persist_*_outputs`).
- Site config (input): `data/sites/<site_key>.json`.
- GHCN cache (input): `data/rainfall/GHCN_<ghcn_station_id>.pkl` (rainfall) and/or `data/air_temp/GHCN_<ghcn_station_id>.pkl` (temperature).

### Folder — sea level (different from rainfall/air-temperature)

Sea level does **not** split into `figures/`/`tables/` subfolders — everything (PNG, HTML, CSV, JSON) goes directly into one per-site directory:

```
outputs/<site_tag>/         # figures AND tables together, no figures/tables split
```

- `site_output_dir = Path('../../../../outputs') / build_site_tag(site_name, site_lon, site_lat)`, created with `site_output_dir.mkdir(parents=True, exist_ok=True)`.
- Site config (input): `data/sites/palau.json` (fixed filename, see `assistant/skills/sea-level-site-setup/SKILL.md`).
- UHSLC/CMEMS cache (input): `data/sea_level/d<uhslc_id>.nc`, `h<uhslc_id>.nc`, `cmems_L4_SSH_0.125deg_<start_year>_<end_year>.nc`.

### Canonical figure filenames — rainfall (`notebooks/historical/National/rainfall/`)

| Notebook | Base name | Format |
|---|---|---|
| `a_Total_rainfall.ipynb` | `F5_Rain_daily` | `.html` (plotly) |
| `a_Total_rainfall.ipynb` | `F5_Rain_annual_max` | `.html` (plotly) |
| `a_Total_rainfall.ipynb` | `F5_Rain_accum` | `.png` (via `plot_bar_probs`) |
| `a_Total_rainfall.ipynb` | `F5_Rain_anom_top10` | `.png` |
| `a_Total_rainfall.ipynb` | `F6a_Rain_dry_season` | `.png` |
| `a_Total_rainfall.ipynb` | `F6a_Rain_wet_season` | `.png` |
| `a_Total_rainfall.ipynb` | `F5_Rain_mean_ONI_daily` | `.png` |
| `a_Total_rainfall.ipynb` | `F5_Rain_mean_ONI_accum` | `.png` |
| `b_Consecutive_dry_days.ipynb` | `F6a_Wet_dry_distribution` | `.png` |
| `b_Consecutive_dry_days.ipynb` | `F6a_Number_dry` | `.png` |
| `b_Consecutive_dry_days.ipynb` | `F6b_Mean_consecutive_dry` | `.png` |
| `b_Consecutive_dry_days.ipynb` | `F6b_Consecutive_dry` | `.png` |
| `c_Heavy_rainfall.ipynb` | `F7a_Wet_dry_distribution` | `.png` |
| `c_Heavy_rainfall.ipynb` | `F7a_Wet_days_1mm` | `.png` |
| `c_Heavy_rainfall.ipynb` | `F7b_Wet_days_95p` | `.png` |

Optional diagnostic filename for accumulated rainfall: `F5_Rain_accum_plot_bar_probs_<station_id>_<station_name>.png`.

### Canonical figure filenames — air temperature (`notebooks/historical/National/air_temperature/`)

| Notebook | Base name | Format |
|---|---|---|
| `a_mean_temperature.ipynb` | `F2_ST_Mean` | `.png` (via `plot_bar_probs`) |
| `a_mean_temperature.ipynb` | `F2_ST_Annomalies_top10` | `.png` |
| `b_min_max_temperature.ipynb` | `F3_ST_min` | `.html` + `.png` (via `plot_timeseries_interactive`) |
| `b_min_max_temperature.ipynb` | `F3_ST_max` | `.html` + `.png` |
| `b_min_max_temperature.ipynb` | `F3_ST_min_max` | `.html` + `.png` |
| `c_hot_cold_days.ipynb` | `F4_ST_hot_cold` | `.html` + `.png` |
| `c_hot_cold_days.ipynb` | `F4_ST_hot_cold_percentiles` | `.html` + `.png` |

Save matplotlib: `plt.savefig(site_figures_dir / build_output_filename(...), dpi=300, bbox_inches='tight')`.
Save plotly: `fig.write_html(site_figures_dir / build_output_filename(..., ext='html'))` and, where applicable, `fig.write_image(site_figures_dir / build_output_filename(...))`.

### Canonical table / JSON filenames — rainfall (`R_*` prefix)

**Notebook `a_Total_rainfall.ipynb`** (`persist_total_rainfall_outputs`):
- `R_mean_annual_<site_tag>.csv`
- `R_mean_summary_table_<site_tag>.csv`
- `R_top10_wettest_years_<site_tag>.csv`
- `R_dry_season_annual_<site_tag>.csv`
- `R_wet_season_annual_<site_tag>.csv`
- `R_ONI_annual_<site_tag>.csv`
- `R_mean_summary_metrics_<site_tag>.json`

**Notebook `b_Consecutive_dry_days.ipynb`** (`persist_dry_days_outputs`):
- `R_dry_days_per_year_<site_tag>.csv`
- `R_consecutive_dry_max_per_year_<site_tag>.csv`
- `R_consecutive_dry_mean_per_year_<site_tag>.csv`
- `R_dry_summary_table_<site_tag>.csv`
- `R_dry_summary_metrics_<site_tag>.json`

**Notebook `c_Heavy_rainfall.ipynb`** (`persist_heavy_rainfall_outputs`):
- `R_wet_days_per_year_<site_tag>.csv`
- `R_heavy_days_per_year_<site_tag>.csv`
- `R_heavy_summary_table_<site_tag>.csv`
- `R_heavy_summary_metrics_<site_tag>.json`

### Canonical table / JSON filenames — air temperature (`T_*` prefix)

**Notebook `a_mean_temperature.ipynb`** (`persist_mean_temperature_outputs`):
- `T_mean_annual_<site_tag>.csv`
- `T_mean_summary_table_<site_tag>.csv`
- `T_mean_top10_warmest_years_<site_tag>.csv`
- `T_mean_ONI_annual_<site_tag>.csv`
- `ENSO_temperature_summary_<site_tag>.csv`
- `T_mean_summary_metrics_<site_tag>.json`

**Notebook `b_min_max_temperature.ipynb`** (`persist_minmax_temperature_outputs`):
- `T_minmax_annual_<site_tag>.csv`
- `T_minmax_summary_table_<site_tag>.csv`
- `T_minmax_summary_metrics_<site_tag>.json`

**Notebook `c_hot_cold_days.ipynb`** (`persist_hot_cold_outputs`):
- `T_hot_days_per_year_<site_tag>.csv`
- `T_cold_nights_per_year_<site_tag>.csv`
- `T_hot_cold_summary_table_etccdi_<site_tag>.csv`
- `T_hot_cold_summary_table_percentiles_<site_tag>.csv`
- `T_hot_cold_summary_metrics_<site_tag>.json`

### Canonical filenames — Regional tropical cyclones (`TC_regional_*`)

Regional cyclone figures go to `outputs/figures/regional_pacific/`:

- `TC_regional_subregions_pacific.png`
- `TC_regional_genesis_tracks_pacific.png`
- `TC_regional_monthly_genesis_pacific.png`
- `TC_regional_track_density_pacific.png`
- `TC_regional_period_comparison_pacific.png`
- `TC_regional_annual_counts_pacific.png`
- `TC_regional_intensity_composition_pacific.png`
- `TC_regional_map_dashboard_pacific.png`
- `TC_regional_ace_pacific.png`

Optional Regional annual tables go to `outputs/tables/regional_tropical_cyclones/`. National cyclone notebooks currently use legacy `F8_TCs_*`/`F9_TCs_*` filenames under `matrix_cc/figures`; migrate them to a per-site output convention deliberately before documenting new canonical National paths.

### Canonical filenames — sea level (`SL_*` prefix, `F10`/`F11` figures)

**Notebook `a_sea_level_trend.ipynb`**:
- `F10_SeaLevel_map.png`, `F10_SeaLevel_trends.png`
- `SL_magnitude_map.png`, `SL_magnitude_timeseries.png`
- `SL_magnitude_results.csv`, `SL_trend_summary_metrics.json`
- `ENSO_SL_influence_summary.csv`, `SL_ONI_scatter.png`

**Notebook `b_sea_level_anomaly.ipynb`**:
- `1_2_2_SL_anomaly_annual_map_decadal.png`
- `SL_anomaly_yearly_mean.csv`, `SL_anomaly_monthly_series.csv`
- `SL_anomaly_summary_metrics.json`

**Notebook `c_sea_level_ff.ipynb`**:
- `F11_Minor_flood_matrix.png`
- `SL_FloodFrequency_threshold_counts_days.png`, `SL_FloodFrequency_threshold_counts_heatmap.png`
- `SL_flood_days_per_year.csv`, `SL_flood_hours_per_year.csv`
- `SL_flood_frequency_summary_metrics.json`

**Notebook `d_sea_level_rankings.ipynb`**:
- `SL_rankings_<station_name>.png`
- `SL_top_10_table.csv`, `SL_top_10_table.json`

Sea-level filenames are **not** suffixed with `_<site_tag>` the way rainfall/air-temperature outputs are (they don't call `build_output_filename`) — they are written directly under the per-site `outputs/<site_tag>/` folder instead, so collisions are avoided by directory rather than by filename suffix. Do not add a `<site_tag>` suffix to a sea-level filename unless the notebook code is changed to do so.

### Hard rules

- Never overwrite a different site's outputs. Always re-derive `site_tag` from the loaded config.
- Cached pickle/NetCDF is keyed by **station ID** (GHCN) or **UHSLC ID**; figures/tables are keyed by **site tag**.
- Use `persist_*_outputs` for rainfall/air-temperature tables — do not call `style_matrix` alone without persisting. Sea level uses `save_table_to_csv`/`save_dict_json` directly instead of a `persist_*_outputs` wrapper.
- Rainfall outputs use the `R_`/`F5`/`F6`/`F7` prefixes; air-temperature outputs use `T_`/`F2`/`F3`/`F4`; sea-level outputs use `SL_`/`F10`/`F11`. Don't mix them.
