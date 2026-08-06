---
name: regional-setup
description: Scan every GHCN-Daily station inside the Pacific EEZ area, quality-filter each one, and collect accepted stations' cleaned daily data into one dictionary for regional rainfall/air-temperature analysis. Use when working on notebooks/historical/Regional/00_regional_setup.ipynb or before any regional (multi-station, Pacific-wide) rainfall/temperature indicator or map.
---

## Skill: Regional Site Setup (notebook `notebooks/historical/Regional/00_regional_setup.ipynb`)

### Purpose
Scan **every** GHCN-Daily station inside the Pacific EEZ area of interest, quality-filter each one, and collect the stations that pass — together with their cleaned daily data — into a single dictionary. This is the multi-station counterpart of the single-site `notebooks/historical/National/00_site_setup.ipynb`: that notebook sets up **one** station picked interactively; this one sets up **many** at once so `notebooks/historical/Regional/rainfall/regional_indicators.ipynb` and `notebooks/historical/Regional/air_temperature/regional_indicators.ipynb` can build multi-station/regional maps without repeating the single-site workflow by hand.

Rainfall and air-temperature share this one setup notebook (both variables are pulled from the same GHCN daily record per station). **Sea level has no regional setup notebook** — see `assistant/skills/regional-sea-level/SKILL.md` for what that would take.

### Required inputs / parameters
- `region_key` — short name used in every output filename (e.g. `"pacific"`).
- `vars_of_interest` — default `["TMIN", "TMAX", "PRCP"]`; a station is a candidate if its inventory reports **at least one**.
- `min_years_before_download` — default `20`; cheap metadata-only filter (minimum record-year span for any variable of interest) applied before downloading any daily data.
- `completeness_threshold` — default `0.75`; same month/year completeness filter as the National `00_site_setup.ipynb` (`filter_by_time_completeness`).
- `min_years_after_filter` — default `20`; a station is rejected if fewer than this many years survive the completeness filter. This is the same `min_years` guard `RegionalMapConfig` uses downstream.
- `max_stations` — default `None`; optional cap for a quick test run over a large area.
- `max_workers` — default `8`; number of stations downloaded in parallel (thread pool — I/O-bound, waiting on NOAA, not CPU-bound).
- `force_redownload` — default `False`; bypasses the per-station cache.

### Workflow
1. **Area of interest** — load the Pacific EEZ polygons (`load_pacific_eez` from `functions/rainfall_regional.py`, shapefile at `data/regional/Pacific_EEZs/*.shp` — this repo's own copy, not an external folder), buffered outward by `EEZ_BUFFER_DEG` so real coastal stations aren't excluded by coordinate-rounding/coastline-simplification artifacts.
2. **Catalog + spatial filter** — download the full GHCN station list and inventory (same source as the National setup), keep only stations whose coordinates fall inside a buffered EEZ polygon (`geopandas.sjoin(..., predicate="intersects")`), tag each with its `eez_country`.
3. **Metadata pre-filter** — drop stations that clearly won't pass before downloading any daily data: must report at least one `vars_of_interest` variable and have at least `min_years_before_download` years of combined record (`GHCN.summarize_record_years`).
4. **Download, clean, filter every candidate in parallel** — for each candidate: download the variables it reports, derive `TMEAN`/`diff` when both `TMIN`/`TMAX` are present, apply `filter_by_time_completeness`, keep only if at least `min_years_after_filter` years survive. A station whose processing raises an error is recorded as rejected (with the error as reason) rather than stopping the batch. Raw per-station downloads are cached at `data/regional/<region_key>/GHCN_<station_id>.pkl` so re-running after tweaking filters doesn't re-hit NOAA.
5. **Inspect** — static sanity-check maps at each stage (candidates vs. dropped by EEZ containment, by metadata pre-filter, by completeness filter), reusing `create_pacific_base_map`.
6. **Save** — the combined dictionary and a metadata-only summary.

### Output contract
- `data/regional/<region_key>_stations.pkl` — `{station_id: {..metadata.., "data": DataFrame}}` for every accepted station.
- `data/regional/<region_key>_summary.json` — metadata-only summary of accepted **and** rejected stations, with the rejection reason.
- `data/regional/<region_key>/GHCN_<station_id>.pkl` — per-station raw cache (pre-filter).

### Common follow-up actions
- After saving, recommend `Regional/rainfall/regional_indicators.ipynb` and/or `Regional/air_temperature/regional_indicators.ipynb`, depending on which variables the user needs.
- If a station has neither `TMIN`/`TMAX` nor `PRCP` after filtering, it's simply absent from the dictionary — don't treat that as an error.

### Hard rules
- Do not skip the EEZ containment step or fall back to a lon/lat bounding box or country-code list — the buffered-polygon method is what correctly excludes mainland Australia/NZ/Asia/Americas while keeping island territories that share a mainland country's GHCN ID prefix.
- Use the same `completeness_threshold` as the single-site setup notebook unless the user explicitly asks for a different one.
- Never write outputs outside `data/regional/`.
