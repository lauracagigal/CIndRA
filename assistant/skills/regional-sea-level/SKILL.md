---
name: regional-sea-level
description: Explains that no regional (multi-station, Pacific-wide) sea-level workflow exists yet, what draft pieces are available to build one (functions/cindra_regional_plotting_helpers.py), and what's still missing. Use when asked for a regional/Pacific-wide sea-level map or indicator, so the gap is stated accurately instead of improvising one.
---

## Skill: Regional Sea Level (notebook `notebooks/historical/Regional/regional_plots.ipynb` — not yet built)

### Status
**This workflow does not exist yet.** It is documented alongside `regional-atmosphere/SKILL.md` so the gap remains visible — not so an assistant can pretend the capability is already there. If a user asks for a regional/Pacific-wide sea-level map or a multi-station sea-level indicator, say plainly that it isn't built yet and point at what already exists to build it from (below), rather than improvising an ad-hoc figure or reusing the National single-site helpers as if they already generalized to many stations.

Concretely, as of this repository merge:
- `notebooks/historical/Regional/regional_plots.ipynb` is a valid markdown-only placeholder included in the Jupyter Book; it contains no analysis or figures.
- There is **no** `Regional/00_regional_setup.ipynb` equivalent for sea level — no notebook scans multiple UHSLC stations the way `Regional/00_regional_setup.ipynb` scans multiple GHCN stations. The National sea-level setup (`sea_level/0_site_setup.ipynb`) configures exactly one hardcoded site (see `assistant/skills/sea-level-site-setup/SKILL.md`).
- `functions/cindra_regional_plotting_helpers.py` holds two **draft/experimental** plotting helpers clearly aimed at this future workflow, but neither is imported by any notebook.

### What already exists to build this from
- `functions/cindra_regional_plotting_helpers.py`:
  - `plot_regional_altimetry_trend_map_filled_tide_gauges(trend_mag_cm, station_df=None, ...)` — gridded absolute-altimetry sea-level change map (cm/epoch) with optional filled circles for relative tide-gauge stations (QC-passed trend, cm/epoch) laid over it. Expects `trend_mag_cm` as an `xarray.DataArray` with lon/lat coordinates, and `station_df` with lon/lat + a `sea_level_change_cm`-style column.
  - `plot_regional_flood_frequency_overview(matrix_df, annual_totals, station_latitudes=None, ...)` — station-year flood-day heatmap (rows = UHSLC stations, north-to-south when `station_latitudes` is given; columns = storm years) plus a lower panel of regional annual total flood-day counts.
- `functions/rainfall_regional.py`'s EEZ-map machinery (`load_pacific_eez`, `create_pacific_base_map`, `RegionalMapConfig`, `build_sites_map_dataframe`, `plot_annual_regional_map`) is the established pattern for "one value per Pacific station on an EEZ base map" — a real regional sea-level workflow should extend this pattern (or the two draft helpers above) rather than reinvent a third map style.
- `functions/sea_level.py`'s per-station calculations (`process_trend_with_nan`, `detect_enso_events`, `get_top_ten`, etc.) are already station-agnostic in principle; what's missing is (a) a multi-station UHSLC discovery/download step analogous to `Regional/00_regional_setup.ipynb`, and (b) a notebook that loops those calculations over many stations the way `Regional/rainfall/regional_indicators.ipynb` loops `_station_rainfall_indicators` over many GHCN stations.

### If a user wants this built
Outline the missing pieces rather than faking output:
1. A `Regional/sea_level/00_regional_setup.ipynb`-style notebook: discover/select multiple UHSLC stations in the Pacific EEZ area (reusing `select_uhslc_station`'s pattern, generalized to "all stations in the EEZ" the way `Regional/00_regional_setup.ipynb` generalized GHCN's single-station picker), download+cache each, save a `data/regional/<region_key>_sl_stations.pkl`-style dictionary.
2. A `Regional/sea_level/regional_indicators.ipynb`-style notebook: loop the National sea-level trend/flood-frequency calculations over that dictionary, save a summary table, and call the two draft helpers in `cindra_regional_plotting_helpers.py` (reviewing/promoting them out of draft status first).
3. Wire the actual `Regional/regional_plots.ipynb` file with real content once the above exists — do not treat its current empty state as "coming soon" content to describe to a user.

### Hard rules
- Never claim a regional/Pacific-wide sea-level figure exists or was generated — it cannot be, since no notebook produces one.
- Never call `plot_regional_altimetry_trend_map_filled_tide_gauges` or `plot_regional_flood_frequency_overview` and present the result as a finished, repo-styled published figure — they are draft/unreviewed. It's fine to use them for exploratory work if the user explicitly asks to try the draft helpers, but label the output as draft/experimental, not a canonical figure.
- Do not read `Regional/regional_plots.ipynb` as if it already contains a workflow — check its size/content before answering questions about it (it may be filled in later; this note is a snapshot, not a permanent fact).
