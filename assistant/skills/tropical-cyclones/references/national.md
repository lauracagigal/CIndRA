# National tropical-cyclone workflow

## Scope

- `notebooks/historical/National/tropical_cyclones/a_tropical_cyclones.ipynb`: all cyclones near a configured site.
- `notebooks/historical/National/tropical_cyclones/b_severe_tropical_cyclones.ipynb`: Category 3+ subset.
- Both currently use the Western Pacific (`basin="WP"`) and extract storms entering a radius around `site_lon`, `site_lat` with `Extract_Circle`.

## Workflow

1. Load a site JSON from `data/sites/` with `site_config_filename` and `load_site_config`.
2. Load or update `data/tcs/tcs_WP.nc` with `download_ibtracs(url, basin="WP")`.
3. Set the IBTrACS variable mapping (`longitude`, `latitude`, `pressure`, `wind`, `time`).
4. Call `Extract_Circle(..., fillwinds=True)` to obtain tracks and closest-approach parameters.
5. Call `get_ibtracs_category` for basin-wide categories when required.
6. Replace unclassified category NaNs with `-1` only for plotting/counting code that expects the sentinel.
7. For severe analysis, filter `category >= 3` and select matching storm coordinates.
8. Generate track, seasonality, category, annual trend, spatial-category and ENSO outputs with `tcs.py` helpers.
9. Build tables with `style_matrix`, `table_tcs_32a`, and `table_tcs_32b` as appropriate.

## National helper map

- Spatial selection and properties: `Extract_Circle`, `GeoDistance`, `GeoAzimuth`.
- Category assignment: `get_ibtracs_category`, `GetStormCategory_wind`, `GetStormCategory_pres`.
- Figures: `Plot_TCs_HistoricalTracks_Category`, `plot_tc_categories_trend`, `plot_bar_probs`, `plot_bar_probs_ONI`.
- ENSO: `download_oni_index`, `add_oni_cat`; current category limits are `[-0.5, 0.5]`.
- Tables: `style_matrix`, `table_tcs_32a`, `table_tcs_32b`.

## Known maintenance cautions

- The notebooks currently use inconsistent `site_key` values (`palau_psw00040309` versus `palau`) and legacy `matrix_cc/figures` paths. Resolve from existing configs and migrate outputs deliberately; never guess silently.
- `fillwinds=True` estimates missing WMO winds from a quadratic pressure–wind fit. Report this when categories depend on filled winds.
- `GetStormCategory_wind` divides WMO 10-minute wind by `0.88` before applying Saffir-Simpson 1-minute thresholds.
- A storm near the site is defined by entering the configured radius, not by genesis basin or landfall.
- Ensure both notebooks use the same cached dataset, site config, radius, analysis window and output convention when comparing all versus severe cyclones.
