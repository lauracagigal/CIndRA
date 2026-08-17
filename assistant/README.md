# CIndRA Assistant — Training Material (PICCM_atmosphere_sealevel)

This folder holds the instructions used to train an external assistant — **CIndRA** (Climate Indicator Research Assistant) — e.g. as a ChatGPT custom GPT. CIndRA covers rainfall, air temperature, sea level, and tropical cyclones across the National site workflows and Regional Pacific workflows in this repository.

## How to use

- **`CIndRA_role.md`** — paste the contents into the "Instructions" / system prompt of the assistant. Defines CIndRA's identity, scope (rainfall + air temperature + sea level + regional), conventions, data sources, analysis rules, plotting rules, output naming, and error handling for all domains. This is background context CIndRA always has, not something conditionally "activated" — it does not follow the Agent Skills format below.
- **`aggregated_CIndRA_markdowns.md`** — single file with **all** markdowns below concatenated (role + skills + this README). Use when the assistant platform accepts one large knowledge file instead of separate uploads (e.g. a ChatGPT custom GPT's knowledge base). Regenerate after any source change: `python assistant/build_aggregated_CIndRA.py`.
- **`skills/`** — one workflow-specific [Agent Skill](https://github.com/anthropics/skills) per notebook/topic: `skills/<name>/SKILL.md`, each with `name`/`description` YAML frontmatter per the [Agent Skills spec](https://agentskills.io/specification). In Claude Code / other Agent-Skills-aware clients, drop this whole `skills/` folder somewhere the client discovers skills from (e.g. `.claude/skills/`) and each one loads on demand. For a ChatGPT custom GPT (which has no skill-activation mechanism), instead upload each `SKILL.md` as a knowledge file, or use `aggregated_CIndRA_markdowns.md` for a single upload:

| Skill name | Notebook / scope |
|---|---|
| `site-setup` | `notebooks/historical/National/00_site_setup.ipynb` — shared entry point for rainfall + air temperature; not under `rainfall/` or `air_temperature/` |
| `total-rainfall` | `National/rainfall/a_Total_rainfall.ipynb` |
| `consecutive-dry-days` | `National/rainfall/b_Consecutive_dry_days.ipynb` |
| `heavy-rainfall` | `National/rainfall/c_Heavy_rainfall.ipynb` |
| `mean-temperature` | `National/air_temperature/a_mean_temperature.ipynb` |
| `min-max-temperature` | `National/air_temperature/b_min_max_temperature.ipynb` |
| `hot-cold-days` | `National/air_temperature/c_hot_cold_days.ipynb` |
| `sea-level-site-setup` | `National/sea_level/0_site_setup.ipynb` — sea level's own entry point, not shared with the other two domains |
| `trend-analysis` | `National/sea_level/a_sea_level_trend.ipynb` |
| `anomaly-analysis` | `National/sea_level/b_sea_level_anomaly.ipynb` |
| `flood-frequency` | `National/sea_level/c_sea_level_ff.ipynb` |
| `rankings` | `National/sea_level/d_sea_level_rankings.ipynb` |
| `regional-setup` | `Regional/00_regional_setup.ipynb` — shared entry point for regional rainfall + air temperature |
| `regional-rainfall` | `Regional/rainfall/regional_indicators.ipynb` |
| `regional-temperature` | `Regional/air_temperature/regional_indicators.ipynb` |
| `tropical-cyclones` | National site-radius and Regional Pacific-subregion IBTrACS/ONI workflows; `functions/tcs.py` |
| `regional-sea-level` | Documents what's missing for a regional sea-level workflow (none exists yet) — kept at the same level of detail as the two built regional domains so the gap doesn't get lost |
| `functions-api` | Callable functions (all domains), `indicators_setup` discovery, `plot_bar_probs` |
| `output-conventions` | Figure / table naming and folders (all domains) |
| `data-sources` | GHCN-Daily, UHSLC, CMEMS, ONI, units, citations (all domains) |

## Repository quick map

- `notebooks/historical/National/00_site_setup.ipynb` — shared entry point for rainfall + air temperature; run before anything under `rainfall/` or `air_temperature/`.
- `notebooks/historical/National/rainfall/` (`a_Total_rainfall.ipynb`, `b_Consecutive_dry_days.ipynb`, `c_Heavy_rainfall.ipynb`) and `notebooks/historical/National/air_temperature/` (`a_mean_temperature.ipynb`, `b_min_max_temperature.ipynb`, `c_hot_cold_days.ipynb`) — the two atmosphere indicator-specific analysis folders. Both use bare `a_`/`b_`/`c_` filename prefixes but live in different folders — disambiguate by folder or full filename, not by the bare letter.
- `notebooks/historical/National/sea_level/` (`0_site_setup.ipynb`, `a_sea_level_trend.ipynb`, `b_sea_level_anomaly.ipynb`, `c_sea_level_ff.ipynb`, `d_sea_level_rankings.ipynb`) — the sea-level workflow, with its **own** site setup (a single hardcoded Palau site today, not the multi-site GHCN picker the atmosphere `00_site_setup.ipynb` has).
- `notebooks/historical/National/tropical_cyclones/` — all and severe tropical cyclones entering a radius around a configured site, using IBTrACS and ONI.
- `notebooks/historical/Regional/` includes multi-station rainfall/temperature and the independent `tropical_cyclones/regional_indicators.ipynb` all-basin IBTrACS workflow. `regional_plots.ipynb` remains an empty sea-level placeholder.
- `functions/` also includes `tcs.py`, the canonical National and Regional tropical-cyclone calculations, tables, and plotting helpers.
- `data/rainfall/` — cached per-station GHCN pickles for `PRCP` (`GHCN_<station_id>.pkl`).
- `data/air_temp/` — cached per-station GHCN pickles for `TMIN`/`TMAX`.
- `data/sea_level/` — cached UHSLC NetCDF (`d<id>.nc`/`h<id>.nc`) and CMEMS NetCDF (`cmems_L4_SSH_*.nc`).
- `data/tcs/` — cached IBTrACS NetCDF and ONI pickle used by cyclone notebooks.
- `data/regional/` — multi-station pickles/summaries from `00_regional_setup.ipynb`, plus an `era5_cache/` subfolder.
- `data/sites/` — per-site config JSON files. `<country_slug>_<ghcn_station_id>.json` for rainfall/air-temperature (shared between both); a fixed `palau.json` for sea level.
- `outputs/figures/<site_tag>/` and `outputs/tables/<site_tag>/` — per-site figure/table outputs (rainfall, air-temperature; PNG/HTML and CSV/JSON respectively). Sea level persists to its own output directory — see `skills/output-conventions/SKILL.md`.

## Updating the assistant

- When you add or rename a function in `functions/` or change `indicators_setup` usage, update `skills/functions-api/SKILL.md` and the **Functions API** section of `CIndRA_role.md` in the same PR.
- When you introduce a new persisted artifact (figure / CSV / JSON), document it in `skills/output-conventions/SKILL.md`.
- When a new analysis notebook is added, mirror its workflow in a new `skills/<name>/SKILL.md` (kebab-case `name` matching the directory, `description` stating what it does *and* when to use it — see the [Agent Skills spec](https://agentskills.io/specification)), extend `CIndRA_role.md`, and add the new `SKILL.md` path to `SOURCE_FILES` in `build_aggregated_CIndRA.py`.
- Validate a skill's frontmatter with the [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) reference tool: `skills-ref validate assistant/skills/<name>`.
- When `Regional/regional_plots.ipynb` gets real content, or a regional sea-level workflow is built, update the [Regional Workflows](CIndRA_role.md#cindra-regional-workflows) section of `CIndRA_role.md` and stop describing them as empty/unbuilt.
- After editing any markdown in `assistant/` or `assistant/skills/`, run `python assistant/build_aggregated_CIndRA.py` to refresh `aggregated_CIndRA_markdowns.md`.
