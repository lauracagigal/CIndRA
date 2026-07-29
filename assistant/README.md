# CIndRA Assistant — Training Material (PICCM_atmosphere_sealevel)

This folder holds the instructions used to train an external assistant — **CIndRA** (Climate Indicator Research Assistant) — e.g. as a ChatGPT custom GPT. CIndRA is the single assistant for the whole [PICCM_atmosphere_sealevel](https://github.com/lauracagigal/PICCM_atmosphere_sealevel) repository (merged from the former `PICCM_Atmosphere` and `PICCM_SeaLevel` repositories): the rainfall notebooks (`notebooks/historical/National/rainfall/`), the air-temperature notebooks (`notebooks/historical/National/air_temperature/`), the sea-level notebooks (`notebooks/historical/National/sea_level/`), the two site-setup notebooks they use, and the Regional rainfall/air-temperature workflow.

## How to use

- **`CIndRA_role.md`** — paste the contents into the "Instructions" / system prompt of the assistant. Defines CIndRA's identity, scope (rainfall + air temperature + sea level + regional), conventions, data sources, analysis rules, plotting rules, output naming, and error handling for all domains.
- **`aggregated_CIndRA_markdowns.md`** — single file with **all** markdowns below concatenated (role + skills + this README). Use when the assistant platform accepts one large knowledge file instead of separate uploads. Regenerate after any source change: `python assistant/build_aggregated_CIndRA.py`.
- **`skills/`** — modular workflow-specific instructions. Attach each file as a separate knowledge document, or use `aggregated_CIndRA_markdowns.md` for a single upload:

| File | Notebook / scope |
|---|---|
| `site_setup.md` | `notebooks/historical/National/00_site_setup.ipynb` — shared entry point for rainfall + air temperature; not under `rainfall/` or `air_temperature/` |
| `total_rainfall.md` | `National/rainfall/a_Total_rainfall.ipynb` |
| `consecutive_dry_days.md` | `National/rainfall/b_Consecutive_dry_days.ipynb` |
| `heavy_rainfall.md` | `National/rainfall/c_Heavy_rainfall.ipynb` |
| `mean_temperature.md` | `National/air_temperature/a_mean_temperature.ipynb` |
| `min_max_temperature.md` | `National/air_temperature/b_min_max_temperature.ipynb` |
| `hot_cold_days.md` | `National/air_temperature/c_hot_cold_days.ipynb` |
| `sea_level_site_setup.md` | `National/sea_level/0_site_setup.ipynb` — sea level's own entry point, not shared with the other two domains |
| `trend_analysis.md` | `National/sea_level/a_sea_level_trend.ipynb` |
| `anomaly_analysis.md` | `National/sea_level/b_sea_level_anomaly.ipynb` |
| `flood_frequency.md` | `National/sea_level/c_sea_level_ff.ipynb` |
| `rankings.md` | `National/sea_level/d_sea_level_rankings.ipynb` |
| `functions_api.md` | Callable functions (all domains), `indicators_setup` discovery, `plot_bar_probs` |
| `output_conventions.md` | Figure / table naming and folders (all domains) |
| `data_sources.md` | GHCN-Daily, UHSLC, CMEMS, ONI, units, citations (all domains) |

## Repository quick map

- `notebooks/historical/National/00_site_setup.ipynb` — shared entry point for rainfall + air temperature; run before anything under `rainfall/` or `air_temperature/`.
- `notebooks/historical/National/rainfall/` (`a_Total_rainfall.ipynb`, `b_Consecutive_dry_days.ipynb`, `c_Heavy_rainfall.ipynb`) and `notebooks/historical/National/air_temperature/` (`a_mean_temperature.ipynb`, `b_min_max_temperature.ipynb`, `c_hot_cold_days.ipynb`) — the two atmosphere indicator-specific analysis folders. Both use bare `a_`/`b_`/`c_` filename prefixes but live in different folders — disambiguate by folder or full filename, not by the bare letter.
- `notebooks/historical/National/sea_level/` (`0_site_setup.ipynb`, `a_sea_level_trend.ipynb`, `b_sea_level_anomaly.ipynb`, `c_sea_level_ff.ipynb`, `d_sea_level_rankings.ipynb`) — the sea-level workflow, with its **own** site setup (a single hardcoded Palau site today, not the multi-site GHCN picker the atmosphere `00_site_setup.ipynb` has).
- `notebooks/historical/Regional/` (`00_regional_setup.ipynb`, `rainfall/regional_indicators.ipynb`, `air_temperature/regional_indicators.ipynb`, `regional_plots.ipynb`) — multi-station Pacific-wide rainfall/air-temperature indicators and maps. `regional_plots.ipynb` is currently an empty placeholder. There is no regional sea-level workflow yet.
- `functions/` — `site_common.py` (shared site-config/output-path helpers), `rainfall.py` and `air_temp.py` (persist helpers re-exporting `site_common.py`), `temp_func.py` (ETCCDI percentile helpers), `data_downloaders.py` (GHCN, ONI, UHSLC cache lookup), `rainfall_regional.py` (regional indicators + Pacific EEZ maps + ERA5 backgrounds), `sea_level.py` (sea-level calculations, partly re-using `site_common.py`), `sea_level_plotting.py` (every sea-level figure), `cindra_regional_plotting_helpers.py` (draft regional sea-level plotting helpers, not yet wired into a notebook).
- `data/rainfall/` — cached per-station GHCN pickles for `PRCP` (`GHCN_<station_id>.pkl`).
- `data/air_temp/` — cached per-station GHCN pickles for `TMIN`/`TMAX`.
- `data/sea_level/` — cached UHSLC NetCDF (`d<id>.nc`/`h<id>.nc`) and CMEMS NetCDF (`cmems_L4_SSH_*.nc`).
- `data/regional/` — multi-station pickles/summaries from `00_regional_setup.ipynb`, plus an `era5_cache/` subfolder.
- `data/sites/` — per-site config JSON files. `<country_slug>_<ghcn_station_id>.json` for rainfall/air-temperature (shared between both); a fixed `palau.json` for sea level.
- `outputs/figures/<site_tag>/` and `outputs/tables/<site_tag>/` — per-site figure/table outputs (rainfall, air-temperature; PNG/HTML and CSV/JSON respectively). Sea level persists to its own output directory — see `skills/output_conventions.md`.

## Updating the assistant

- When you add or rename a function in `functions/` or change `indicators_setup` usage, update `skills/functions_api.md` and the **Functions API** section of `CIndRA_role.md` in the same PR.
- When you introduce a new persisted artifact (figure / CSV / JSON), document it in `skills/output_conventions.md`.
- When a new analysis notebook is added, mirror its workflow in a new `skills/<name>.md`, extend `CIndRA_role.md`, and add the file to `SOURCE_FILES` in `build_aggregated_CIndRA.py`.
- When `Regional/regional_plots.ipynb` gets real content, or a regional sea-level workflow is built, update the [Regional Workflows](CIndRA_role.md#cindra-regional-workflows) section of `CIndRA_role.md` and stop describing them as empty/unbuilt.
- After editing any markdown in `assistant/` or `assistant/skills/`, run `python assistant/build_aggregated_CIndRA.py` to refresh `aggregated_CIndRA_markdowns.md`.
