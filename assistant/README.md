# CIndRA Assistant — Training Material

This folder holds the English-first instructions used to configure an external assistant — **CIndRA** (Climate Indicator Research Assistant), for example on a custom-assistant platform. Its authoritative code source is [github.com/lauracagigal/CIndRA](https://github.com/lauracagigal/CIndRA). CIndRA covers only the National and Regional indicators implemented in that repository; computed answers and figures require actual execution of the corresponding repository workflow.

## How to use

On an external platform, give the assistant access to a current clone or retrievable
copy of `https://github.com/lauracagigal/CIndRA` and an execution environment capable
of running its notebooks. Uploading these instructions alone does not authorize the
assistant to invent calculations: if it cannot retrieve and execute the repository,
it must limit itself to documented explanations and state that computed outputs are
unavailable.

- **`CIndRA_role.md`** — paste the contents into the "Instructions" / system prompt of the assistant. Defines CIndRA's identity, scope (rainfall + air temperature + sea level + regional), conventions, data sources, analysis rules, plotting rules, output naming, and error handling for all domains. This is background context CIndRA always has, not something conditionally "activated" — it does not follow the Agent Skills format below.
- **`aggregated_CIndRA_markdowns.md`** — single file with **all** markdowns below concatenated (role + skills + this README). Use when the assistant platform accepts one large knowledge file instead of separate uploads (e.g. a ChatGPT custom GPT's knowledge base). Regenerate after any source change: `python assistant/build_aggregated_CIndRA.py`.
- **`skills/`** — one focused [Agent Skill](https://github.com/anthropics/skills) per coherent domain or specialized workflow: `skills/<name>/SKILL.md`, each with `name`/`description` YAML frontmatter per the [Agent Skills spec](https://agentskills.io/specification). Related National atmosphere notebooks and their repeated setup/plotting rules are consolidated by domain. In Claude Code / other Agent-Skills-aware clients, drop this whole `skills/` folder somewhere the client discovers skills from (e.g. `.claude/skills/`) and each one loads on demand. For a ChatGPT custom GPT (which has no skill-activation mechanism), instead upload each `SKILL.md` as a knowledge file, or use `aggregated_CIndRA_markdowns.md` for a single upload:

| Skill name | Notebook / scope |
|---|---|
| `site-setup` | `notebooks/historical/National/00_site_setup.ipynb` — shared entry point for rainfall + air temperature; not under `rainfall/` or `air_temperature/` |
| `national-rainfall` | Complete National rainfall workflow: totals, anomalies, dry spells, wet days and heavy rainfall |
| `national-temperature` | Complete National air-temperature workflow: mean/min/max temperature, diurnal range and hot/cold extremes |
| `sea-surface-temperature` | National selected-EEZ and Regional Pacific SST means, trends, anomalies, NOAA OISST download and `functions/sst.py` |
| `marine-heatwaves` | National EEZ-first/point and Regional Pacific NOAA OISST MHW detection, trends, decadal/ENSO maps and EEZ summaries |
| `marine-biochemistry` | National and Regional pH, chlorophyll-a, phytoplankton size/biomass and dissolved-oxygen workflows |
| `sea-level-site-setup` | `National/sea_level/0_site_setup.ipynb` — sea level's own entry point, not shared with the other two domains |
| `trend-analysis` | `National/sea_level/a_sea_level_trend.ipynb` |
| `anomaly-analysis` | `National/sea_level/b_sea_level_anomaly.ipynb` |
| `flood-frequency` | `National/sea_level/c_sea_level_ff.ipynb` |
| `rankings` | `National/sea_level/d_sea_level_rankings.ipynb` |
| `regional-setup` | `Regional/00_regional_setup.ipynb` — shared entry point for regional rainfall + air temperature |
| `regional-atmosphere` | Regional rainfall and air-temperature indicators, station maps, anomaly series and supported ERA5 backgrounds |
| `tropical-cyclones` | National site-radius and Regional Pacific-subregion IBTrACS/ONI workflows; `functions/tcs.py` |
| `regional-sea-level` | Documents what's missing for a regional sea-level workflow (none exists yet) — kept at the same level of detail as the two built regional domains so the gap doesn't get lost |
| `product-assembly` | Generate and assemble a traceable National/Regional report through repository-native site setup, data caches, notebooks/helpers and canonical figures, followed by inventory, captions, methods, provenance, validation, issue log, and Markdown/DOCX/PDF outputs |
| `functions-api` | Callable functions (all domains), `indicators_setup` discovery, `plot_bar_probs` |
| `output-conventions` | Figure / table naming and folders (all domains) |
| `data-sources` | GHCN-Daily, UHSLC, CMEMS, ONI, units, citations (all domains) |

## Repository quick map

- `notebooks/historical/National/00_site_setup.ipynb` — shared entry point for rainfall + air temperature; run before anything under `rainfall/` or `air_temperature/`.
- `notebooks/historical/National/rainfall/` (`a_Total_rainfall.ipynb`, `b_Consecutive_dry_days.ipynb`, `c_Heavy_rainfall.ipynb`) and `notebooks/historical/National/air_temperature/` (`a_mean_temperature.ipynb`, `b_min_max_temperature.ipynb`, `c_hot_cold_days.ipynb`) — the two atmosphere indicator-specific analysis folders. Both use bare `a_`/`b_`/`c_` filename prefixes but live in different folders — disambiguate by folder or full filename, not by the bare letter.
- `notebooks/historical/National/sea_level/` (`0_site_setup.ipynb`, `a_sea_level_trend.ipynb`, `b_sea_level_anomaly.ipynb`, `c_sea_level_ff.ipynb`, `d_sea_level_rankings.ipynb`) — the sea-level workflow, with its **own** site setup (a single hardcoded Palau site today, not the multi-site GHCN picker the atmosphere `00_site_setup.ipynb` has).
- `notebooks/historical/National/tropical_cyclones/` — all and severe tropical cyclones entering a radius around a configured site, using IBTrACS and ONI.
- `notebooks/historical/National/sea_surface_temperature/` — selected-EEZ SST maps, trends, anomalies, area averages and ONI analysis.
- `notebooks/historical/National/biochemistry/` — selected-EEZ pH, chlorophyll-a, phytoplankton-size and dissolved-oxygen analyses.
- `notebooks/historical/Regional/` includes multi-station rainfall/temperature, regional NOAA OISST and marine heatwaves, five marine-biochemistry notebooks, and the independent `tropical_cyclones/regional_indicators.ipynb` all-basin IBTrACS workflow. `regional_plots.ipynb` is a markdown-only sea-level placeholder.
- `functions/` includes the repository calculations and plotting helpers, including `sst.py`, `marineHeatWaves.py`, `ocean.py`, `tcs.py` and the Regional-biochemistry notebook generator.
- `data/rainfall/` — cached per-station GHCN pickles for `PRCP` (`GHCN_<station_id>.pkl`).
- `data/air_temp/` — cached per-station GHCN pickles for `TMIN`/`TMAX`.
- `data/sea_level/` — cached UHSLC NetCDF (`d<id>.nc`/`h<id>.nc`) and CMEMS NetCDF (`cmems_L4_SSH_*.nc`).
- `data/sea_surface_temperature/` — National SST subsets and the cached regional NOAA OISST monthly NetCDF.
- `data/biochemistry/` and `data/regional/biochemistry/` — National and Pacific-wide marine-biochemistry caches.
- `data/tcs/` — cached IBTrACS NetCDF and ONI pickle used by cyclone notebooks.
- `data/regional/` — multi-station pickles/summaries from `00_regional_setup.ipynb`, plus an `era5_cache/` subfolder.
- `data/sites/` — per-site config JSON files. `<country_slug>_<ghcn_station_id>.json` for rainfall/air-temperature (shared between both); a fixed `palau.json` for sea level.
- `outputs/figures/<site_tag>/` and `outputs/tables/<site_tag>/` — per-site figure/table outputs (rainfall, air-temperature; PNG/HTML and CSV/JSON respectively). Sea level persists to its own output directory — see `skills/output-conventions/SKILL.md`.

## Updating the assistant

- When you add or rename a function in `functions/` or change `indicators_setup` usage, update `skills/functions-api/SKILL.md` and the **Functions API** section of `CIndRA_role.md` in the same PR.
- When you introduce a new persisted artifact (figure / CSV / JSON), document it in `skills/output-conventions/SKILL.md`.
- When a new analysis notebook is added, mirror its workflow in a new `skills/<name>/SKILL.md` (kebab-case `name` matching the directory, `description` stating what it does *and* when to use it — see the [Agent Skills spec](https://agentskills.io/specification)), extend `CIndRA_role.md`, and add the new `SKILL.md` path to `SOURCE_FILES` in `build_aggregated_CIndRA.py`.
- When report-package requirements, validation labels, or report-facing product expectations change, update `skills/product-assembly/SKILL.md` and regenerate the aggregate.
- Validate a skill's frontmatter with the [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) reference tool: `skills-ref validate assistant/skills/<name>`.
- When `Regional/regional_plots.ipynb` gets real content, or a regional sea-level workflow is built, update the [Regional Workflows](CIndRA_role.md#cindra-regional-workflows) section of `CIndRA_role.md` and stop describing them as empty/unbuilt.
- After editing any markdown in `assistant/` or `assistant/skills/`, run `python assistant/build_aggregated_CIndRA.py` to refresh `aggregated_CIndRA_markdowns.md`.
