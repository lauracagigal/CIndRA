---
name: sea-level-site-setup
description: Set up the sea-level analysis site (currently a single hardcoded Palau site) by resolving the UHSLC tide-gauge station, pre-downloading/caching UHSLC and CMEMS data, and saving the site config JSON. Use when starting sea-level analysis or before running any National sea-level notebook (notebooks/historical/National/sea_level/0_site_setup.ipynb).
---

## Skill: Sea-Level Site Setup (notebook `sea_level/0_site_setup.ipynb`)

### Purpose
Define the sea-level site once and save a reusable config file for the four sea-level analysis notebooks (`a_sea_level_trend.ipynb`, `b_sea_level_anomaly.ipynb`, `c_sea_level_ff.ipynb`, `d_sea_level_rankings.ipynb`).

This is **not** the same notebook as the atmosphere `notebooks/historical/National/00_site_setup.ipynb`, and the two are not interchangeable: this one lives at `notebooks/historical/National/sea_level/0_site_setup.ipynb` (single leading `0`), configures UHSLC/CMEMS sources instead of GHCN, and — unlike the atmosphere setup — is currently a **single hardcoded site**, not an interactive multi-station picker.

### Inputs the assistant must collect
In principle, the same shape of inputs as the atmosphere setup (site name, coordinates, station filter, analysis window), but today the notebook has them hardcoded for Palau:
- `site_name = "Palau"`, `site_lon = 134.620`, `site_lat = 7.340`.
- `station_country_filter = "Palau"` — used by `select_uhslc_station` to filter UHSLC candidates.
- `selected_uhslc_id` / `selected_station_name` — both `None` here, so station selection falls back to nearest match within the country filter.
- `site_eez_shapefile` — path to the site's EEZ polygon (`data/Palau_EEZ/pw_eez_pol_april2022.shp`), used to derive the CMEMS bounding box.
- `start_date` / `end_date` — nominal analysis window (`"1993-01-01"` / `"2022-12-31"`).
- `cmems_bbox_override` — `None` by default (bbox derived from the EEZ shapefile); set explicitly to skip the shapefile lookup.
- `cmems_start_datetime` / `cmems_end_datetime` — CMEMS download window, ISO 8601 with time (`"1993-01-01T00:00:00"` / `"2025-04-30T23:59:59"`).

### Workflow
1. Build the `site_config` dict with the fields above (edit the literal in the notebook to point at a different site/EEZ — there is no interactive station picker to fall back on).
2. `prepare_site_data(site_config, sea_level_data_dir)` (from `sea_level.py`) does all the work:
   - Resolves the UHSLC station via `select_uhslc_station(...)`, adding `selected_uhslc_id`, `station`, `country`, `station_lon`, `station_lat`, `station_distance_km` to the config.
   - Downloads/caches daily + hourly UHSLC NetCDF via `download_uhslc_data(data_dir, uhslc_id, "daily"/"hourly")` — **note:** as of this repository merge, `download_uhslc_data` only serves already-cached files (`data/sea_level/d<id>.nc`, `h<id>.nc`); it raises `FileNotFoundError` with manual-download instructions if nothing is cached yet. Do not tell the user this step "downloads" a new station's data automatically.
   - Downloads/caches the ONI index via `download_oni_index(...)`.
   - Derives the CMEMS bounding box from the EEZ shapefile (or `cmems_bbox_override`) and downloads/caches the CMEMS SSH subset via `get_CMEMS_data(...)` → `cmems_L4_SSH_0.125deg_<start_year>_<end_year>.nc`.
3. `save_site_config(site_config, Path('../../../../data/sites/palau.json'))` — writes the **fixed filename** `palau.json`, not a `site_config_filename(site_key)`-derived one like the atmosphere workflow.

### Output contract
- JSON at `data/sites/palau.json` with all the fields listed above plus the fields `prepare_site_data` adds (`selected_uhslc_id`, `station`, `country`, `station_lon`, `station_lat`, `station_distance_km`, `cmems_path`, `cmems_filename`). See [assets/site_config_template.json](assets/site_config_template.json) for the **input** schema (the dict you construct before calling `prepare_site_data` -- the saved file has the extra derived fields added on top).
- Cached UHSLC NetCDF at `data/sea_level/d<uhslc_id>.nc` (daily) and `data/sea_level/h<uhslc_id>.nc` (hourly), zero-padded to 3 digits.
- Cached CMEMS NetCDF at `data/sea_level/cmems_L4_SSH_0.125deg_<start_year>_<end_year>.nc`.

### Common follow-up actions
- Confirm which UHSLC station was resolved (`station`, `country`, `station_distance_km` from the saved config) before running the downstream notebooks.
- If `download_uhslc_data` raises `FileNotFoundError`, tell the user exactly which file is missing and that it must be downloaded manually from `https://uhslc.soest.hawaii.edu/data/?rq` and placed at the given path — do not silently retry or fabricate a successful download.
- After saving the config, recommend opening `a_sea_level_trend.ipynb` next.

### Hard rules
- Do not invent an interactive station-discovery flow for sea level that does not exist in the notebook — if the user wants a second sea-level site, say the notebook needs to be adapted (duplicate it, or generalize the hardcoded dict into inputs) rather than pretending the capability already exists.
- Never write the site config outside `data/sites/`, and never rename it away from `palau.json` unless the notebook itself is changed to derive a different filename.
- Never write UHSLC/CMEMS caches outside `data/sea_level/`.
- Do not claim `download_uhslc_data` downloads fresh data — it only serves an existing local cache (see Output Conventions / Error Handling in `CIndRA_role.md`).
