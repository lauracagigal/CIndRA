---
name: data-sources
description: Documents every external data source used in this repository (GHCN-Daily, NOAA ONI, UHSLC tide gauges, CMEMS satellite altimetry), their URLs, units, sentinels, and citations, plus reference-period conventions. Use when downloading new data, citing a data source, or converting units.
---

## Skill: Data Sources & Attribution

### Daily precipitation and temperature — GHCN-Daily (NOAA NCEI)

- **Country lookup**: `https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-countries.txt` → `GHCN.download_country_codes()`.
- **Station inventory**: `https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt` → `GHCN.download_stations_info()`.
- **Element inventory**: `https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt` → `GHCN.download_station_inventory()`.
- **Per-station daily CSVs**: `https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/<station_id>.csv`.
- **Variables in use**: `PRCP` (rainfall), `TMIN`/`TMAX` (temperature) — all stored in tenths of the analysis unit; downloader divides by 10.
- **Units after conversion**: daily rainfall **mm/day**; annual accumulated rainfall **mm/year**; temperature **°C**; `TMEAN = (TMAX + TMIN) / 2` and `diff = TMAX − TMIN` derived in `00_site_setup.ipynb`.
- **Sentinels**: `-9999` → NaN inside `extract_dict_data_var`.
- **Documentation**: `https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/doc/GHCND_documentation.pdf`.
- **Citation**: Menne, M.J., I. Durre, R.S. Vose, B.E. Gleason, and T.G. Houston, 2012. *An overview of the Global Historical Climatology Network-Daily Database.* J. Atmos. Oceanic Technol., 29, 897-910.

### ENSO — NOAA ONI (rainfall `a_Total_rainfall.ipynb` and temperature `a_mean_temperature.ipynb`)

- **URL**: `https://psl.noaa.gov/data/correlation/oni.data`.
- **Format**: monthly Niño 3.4 anomalies. `-99.9` → NaN (`download_oni_index`).
- **Classification** (via `add_oni_cat` in `ind_setup`):
  - El Niño: ONI ≥ 0.5 (5 consecutive months for official events; plotting uses monthly categories).
  - La Niña: ONI ≤ −0.5.
  - Neutral otherwise.
- **Colours**: El Niño = red, La Niña = blue, Neutral = gray.
- **Citation**: NOAA Climate Prediction Center / Physical Sciences Laboratory.

### Tide gauge — UHSLC (University of Hawaii Sea Level Center)

- **Portal**: `https://uhslc.soest.hawaii.edu/data/?rq` (Research Quality Data Set).
- **Per-station NetCDF**: daily `d<uhslc_id>.nc`, hourly `h<uhslc_id>.nc` (`uhslc_id` zero-padded to 3 digits, e.g. `d007.nc` for Malakal, Palau), cached under `data/sea_level/`.
- **Lookup helper**: `download_uhslc_data(data_dir, uhslc_id, resolution)` in `data_downloaders.py` — **cache lookup only**, does not download new files (see Hard Rules).
- **Datums**: `get_uhslc_datum(uhslc_id, datum_name)` in `sea_level.py` fetches the live datum table from `https://uhslc.soest.hawaii.edu/stations/TIDES_DATUMS/...` (e.g. `MSL`, `MHHW`).
- **Station discovery**: `select_uhslc_station(...)` in `sea_level.py` queries `https://uhslc.soest.hawaii.edu/data/meta.geojson` and picks the nearest/matching station.
- **Units**: sea level in metres in the raw NetCDF (`sea_level` variable); notebooks convert to cm for reporting (`100 * value`).

### Satellite altimetry — CMEMS (Copernicus Marine Service)

- **Dataset**: `cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D` (global ocean gridded L4, `adt` absolute dynamic topography and `sla` sea level anomaly variables).
- **Access**: the `copernicusmarine` Python package, via `get_CMEMS_data(...)` in `sea_level.py`, which subsets to a bounding box (derived from the site's EEZ shapefile, or `cmems_bbox_override`) and a date range, caching the result as `cmems_L4_SSH_0.125deg_<start_year>_<end_year>.nc` under `data/sea_level/`.
- **Units**: metres in the raw NetCDF; notebooks convert to mm/yr for trends and cm for anomalies/deltas.

### Reference periods / analysis windows

- Rainfall and air-temperature climatology baseline for anomalies: **1961–1990** (WMO standard), stored in site config as `reference_period_start` / `reference_period_end`. Applies to rainfall totals and to mean/min/max temperature anomalies alike.
- In code, slice with `.loc[ref_start:ref_end]` — never pass `"1961:1990"` as a single label to `.loc` on a DatetimeIndex.
- Hot days (TX90p) / cold nights (TN10p) use the same 1961–1990 window as the ETCCDI base period, hardcoded in `temp_func.py` (`BASE_PERIOD_START`/`BASE_PERIOD_END`).
- Sea level has no fixed WMO reference period; each notebook uses the available UHSLC/CMEMS record window (commonly 1993–2022/2025) for trends, and the station's own monthly climatology (not 1961–1990) for anomalies.

### QC applied in the shared `00_site_setup.ipynb`

1. **Download** — concat requested variables, `dropna()`. Temperature additionally derives `TMEAN`/`diff` when both `TMIN` and `TMAX` are present.
2. **Completeness filter** — `filter_by_time_completeness` with `month_threshold = year_threshold = completeness_threshold` (default 0.75), applied independently to the temperature pickle and the rainfall pickle. Months with < 75% of calendar days observed are dropped; years with < 75% of valid months are dropped.

Rainfall notebooks `b_Consecutive_dry_days.ipynb` and `c_Heavy_rainfall.ipynb` do not apply any additional per-notebook completeness filter — the shared `00_site_setup.ipynb` filter is the only one.

### Hard rules

- Always attribute sources in narrative outputs ("Source: GHCN-Daily station <id>", "Source: NOAA ONI", "Source: UHSLC station <id>", "Source: CMEMS L4 SSH").
- Never invent GHCN station IDs; resolve via site config and `GHCN.get_country_code`. Never invent UHSLC station IDs; resolve via `select_uhslc_station` / the saved site config.
- Always state units: **mm**, **mm/day**, **mm/year**, **°C**, **°C/decade**, **days/year** (rainfall/temperature); **mm/yr**, **cm** (sea level).
- Never present user-uploaded data as primary without explicit user instruction.
- Do not claim `download_uhslc_data` fetches new data from UHSLC — it only serves an already-cached local file (`data/sea_level/d<id>.nc` / `h<id>.nc`); automatic download was lost in the PICCM_Atmosphere/PICCM_SeaLevel merge and has not been restored.
